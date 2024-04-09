"""
-- SPDX-License-Identifier: Apache-2.0
/*
    Generic Audit Trigger
    Linear Time Record Version History

    Date:
        2022-02-03

    Purpose:
        Generic audit history for tables including an indentifier
        to enable indexed linear time lookup of a primary key's version history
*/


-- Namespace to "audit"
create schema if not exists audit;


"""
CREATE_AUDIT_OPERATION_ENUM = """
-- Create enum type for SQL operations to reduce disk/memory usage vs text
create type audit.operation as enum (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE'
);
"""

def create_audit_table_for_table(table_name: str):
    return f"""
        create table audit.{table_name}_record_version(
            -- unique auto-incrementing id
            id             BIGINT IDENTITY PRIMARY KEY,
            -- uniquely identifies a record by primary key 
            record_id VARCHAR(26) NOT NULL,
            -- INSERT/UPDATE/DELETE/TRUNCATE/SNAPSHOT
            op             audit.operation NOT NULL,
            ts             TIMESTAMPTZ NOT NULL DEFAULT (now()),
            -- contents of the record
            record         JSONB,
        );

        -- mark the table as configuration data so it's included in database dumps and can be backed up
        select pg_catalog.pg_extension_config_dump('audit.{table_name}_record_version', '');
        select pg_catalog.pg_extension_config_dump('audit.{table_name}_record_version_id_seq', '');

        create index ix_{table_name}_record_version_record_id
            on audit.{table_name}_record_version(record_id)
            where record_id is not null;

        create index ix_{table_name}_record_version_ts
            on audit.{table_name}_record_version
            using brin(ts);
    """


CREATE_PRIMARY_KEY_COLUMNS_FUNCTION = """
    create or replace function audit.primary_key_columns(entity_oid oid)
        returns text[]
        stable
        security definer
        set search_path = ''
        language sql
    as $$
        -- Looks up the names of a table's primary key columns
        select
            coalesce(
                array_agg(pa.attname::text order by pa.attnum),
                array[]::text[]
            ) column_names
        from
            pg_index pi
            join pg_attribute pa
                on pi.indrelid = pa.attrelid
                and pa.attnum = any(pi.indkey)

        where
            indrelid = $1
            and indisprimary
    $$;
"""

TO_RECORD_ID_FUNCTION = """
    create or replace function audit.to_record_id(entity_oid oid, pkey_cols text[], rec jsonb)
        returns uuid
        stable
        language sql
    as $$
        select
            case
                when rec is null then null
                when pkey_cols = array[]::text[] then uuid_generate_v4()
                else (
                    select
                        uuid_generate_v5(
                            '1298dc34-40d1-4039-94ad-4873ba9975db',
                            ( jsonb_build_array(to_jsonb($1)) || jsonb_agg($3 ->> key_) )::text
                        )
                    from
                        unnest($2) x(key_)
                )
            end
    $$;
"""


def create_insert_update_delete_trigger(table_name: str):
    return f"""
        create or replace function audit.{table_name}_insert_update_delete_trigger()
            returns trigger
            security definer
            language plpgsql
        as $$
        declare
            pkey_cols text[] = audit.primary_key_columns(TG_RELID);

            record_jsonb jsonb = to_jsonb(new);
            record_id uuid = audit.to_record_id(TG_RELID, pkey_cols, record_jsonb);
        begin

            insert into audit.record_version(
                record_id,
                op,
                record,
            )
            select
                record_id,
                TG_OP::audit.operation,
                record_jsonb,

            return new;
        end;
        $$;
    """


def create_truncate_trigger_trigger(table_name: str):
    return f"""
        create or replace function audit.{table_name}_truncate_trigger()
            returns trigger
            security definer
            set search_path = ''
            language plpgsql
        as $$
        begin
            insert into audit.{table_name}_record_version(
                op,
            )
            select
                TG_OP::audit.operation,
            return coalesce(old, new);
        end;
        $$;


        create or replace function audit.enable_tracking(regclass)
            returns void
            volatile
            security definer
            set search_path = ''
            language plpgsql
        as $$
        declare
            statement_row text = format('
                create trigger audit_i_u_d
                    after insert or update or delete
                    on %s
                    for each row
                    execute procedure audit.insert_update_delete_trigger();',
                $1
            );

            statement_stmt text = format('
                create trigger audit_t
                    after truncate
                    on %s
                    for each statement
                    execute procedure audit.truncate_trigger();',
                $1
            );

            pkey_cols text[] = audit.primary_key_columns($1);
        begin
            if pkey_cols = array[]::text[] then
                raise exception 'Table % can not be audited because it has no primary key', $1;
            end if;

            if not exists(select 1 from pg_trigger where tgrelid = $1 and tgname = 'audit_i_u_d') then
                execute statement_row;
            end if;

            if not exists(select 1 from pg_trigger where tgrelid = $1 and tgname = 'audit_t') then
                execute statement_stmt;
            end if;
        end;
        $$;


        create or replace function audit.disable_tracking(regclass)
            returns void
            volatile
            security definer
            set search_path = ''
            language plpgsql
        as $$
        declare
            statement_row text = format(
                'drop trigger if exists audit_i_u_d on %s;',
                $1
            );

            statement_stmt text = format(
                'drop trigger if exists audit_t on %s;',
                $1
            );
        begin
            execute statement_row;
            execute statement_stmt;
        end;
        $$;