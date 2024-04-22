from sqlalchemy import Table
import json

from config import settings


def create_graph_nodes_and_edges(table: Table):
    for column in table.columns:
        print(column)
    print("")


def create_vertex_function(table: Table):
    table_name = table.name
    properties = {}
    for column in table.columns:
        if column.info.get("edge_start", False):
            pass
        else:
            properties[column.name] = column.name

    return f"""
        CREATE OR REPLACE FUNCTION {table_name}_create_vertex()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        DECLARE
            vertex ag_catalog.agtype;
        BEGIN
            SET ROLE {settings.DB_SCHEMA}_admin;
            LOAD '$libdir/plugins/age.dylib';
            SELECT *
            FROM ag_catalog.cypher('graph', $trigger$
                CREATE (v:{table_name} {{id: 'ID'}})
            $trigger$) AS (vertex ag_catalog.agtype) INTO vertex;

            RETURN vertex;
        END;
        $$;
    """


def create_vertex_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_create_vertex_trigger
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {table_name}_create_vertex();
    """


def create_edge_function(table: Table):
    table_name = table.name
    return f"""
        CREATE OR REPLACE FUNCTION {table_name}_create_edge()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $BODY$
        DECLARE test ag_catalog.agtype;
        BEGIN
            SET ROLE {settings.DB_SCHEMA}_admin;
            LOAD '$libdir/plugins/age.dylib';
            SET search_path TO ag_catalog, auth, audit, fltr, {settings.DB_SCHEMA};
            SELECT *
            FROM ag_catalog.cypher('graph', $$
                CREATE (v:{table_name})
            $$) AS (v ag_catalog.agtype) INTO test;
            RETURN test;
        END;
        $BODY$;
    """


def create_edge_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_create_edge_trigger
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {table_name}_create_edge();
    """


CREATE_INSERT_META_RECORD_FUNCTION = """
/*
Simple function to create a new meta row and return the id of the new row.
Set as the server_default for the id column in all tables that have a meta column.
*/

CREATE OR REPLACE FUNCTION audit.insert_meta_record() RETURNS VARCHAR AS $$
DECLARE meta_id VARCHAR(26);
BEGIN
    INSERT INTO audit.meta DEFAULT VALUES
    RETURNING id INTO meta_id;
    RETURN meta_id;
END;
$$ LANGUAGE plpgsql;
"""
