"""
    This script is used to create the roles and schemas for the application.
    It is a python script as it needs environment variables to run.
    Create new database, users, and schemas.
    Revoke and Grant appropriate privileges for all users from public schema. 
    In addition, we also set the search_path for the settings defined owner
    and settings defined user to be the settings defined schema.

    NOTE - The use of f strings to provide the schema name and database name DOES NOT 
    provide any protection against SQL injection. You cannot paramaterize postgres DDL 
    statements. The names are defined in the .env file, are not user input, and are only
    used at the beginning of projects to create the initial db.  That said, Don't inject
    SQL into your own database.
"""
from config import settings


def drop_database(db_name):
    return f"""
        -- Drop the database if it exists
        DROP DATABASE IF EXISTS {db_name} WITH (FORCE);
    """


DROP_SCHEMAS = f"""
-- Drop the schemas if they exist
DROP SCHEMA IF EXISTS audit CASCADE;
DROP SCHEMA IF EXISTS auth CASCADE;
DROP SCHEMA IF EXISTS fltr CASCADE;
DROP SCHEMA IF EXISTS {settings.DB_SCHEMA} CASCADE;
"""


DROP_ROLES = f"""
-- Drop the roles if they exist
DROP ROLE IF EXISTS {settings.DB_SCHEMA}_writer;
DROP ROLE IF EXISTS {settings.DB_SCHEMA}_reader;
DROP ROLE IF EXISTS {settings.DB_SCHEMA}_admin;
DROP ROLE IF EXISTS {settings.DB_SCHEMA}_authenticator;
DROP ROLE IF EXISTS {settings.DB_SCHEMA}_base_role;
"""


CREATE_ROLES = f"""
-- Create the base role with permissions that all other users will inherit
CREATE ROLE {settings.DB_SCHEMA}_base_role NOINHERIT;

-- Create the reader role
CREATE ROLE {settings.DB_SCHEMA}_reader INHERIT IN ROLE {settings.DB_SCHEMA}_base_role;

-- Create the writer role
CREATE ROLE {settings.DB_SCHEMA}_writer INHERIT IN ROLE {settings.DB_SCHEMA}_base_role;

-- Create the admin role
CREATE ROLE {settings.DB_SCHEMA}_admin INHERIT IN ROLE {settings.DB_SCHEMA}_base_role;

-- Create the authentication role
CREATE ROLE {settings.DB_SCHEMA}_authenticator NOINHERIT LOGIN PASSWORD '{settings.DB_USER_PW} IN ROLE {settings.DB_SCHEMA}_base_role;';

-- Grant the reader, writer, and admin roles to the authentication role
-- Allows the authentication role to SET ROLE to any of the other roles
GRANT {settings.DB_SCHEMA}_reader,  {settings.DB_SCHEMA}_writer, {settings.DB_SCHEMA}_admin TO {settings.DB_SCHEMA}_authenticator;
"""


def create_database(db_name: str):
    return f"""
        -- Create the database
        CREATE DATABASE {db_name} WITH OWNER = {settings.DB_SCHEMA}_admin;
    """


CREATE_SCHEMAS = f"""
-- Create the uno schemas
CREATE SCHEMA IF NOT EXISTS audit AUTHORIZATION {settings.DB_SCHEMA}_admin;
CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION {settings.DB_SCHEMA}_admin;
CREATE SCHEMA IF NOT EXISTS fltr AUTHORIZATION {settings.DB_SCHEMA}_admin;

-- Create the application schema
CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA} AUTHORIZATION {settings.DB_SCHEMA}_admin;
"""


REVOKE_ACCESS = f"""
-- Remove ability for all users to do everything in public schema
REVOKE ALL ON SCHEMA public FROM public;
REVOKE ALL ON SCHEMA {settings.DB_SCHEMA} FROM public;
REVOKE ALL ON SCHEMA audit FROM public;
REVOKE ALL ON SCHEMA auth FROM public;
REVOKE ALL ON SCHEMA fltr FROM public;
"""


CONFIGURE_PRIVILEGES = f"""
ALTER SCHEMA audit OWNER TO {settings.DB_SCHEMA}_admin;
ALTER TABLE audit.record_version OWNER TO {settings.DB_SCHEMA}_admin;

-- Grant connect privileges to the authenticator
GRANT CONNECT ON DATABASE {settings.DB_NAME} TO {settings.DB_SCHEMA}_authenticator;

-- Grant usage privileges for users to created schemas
-- authenticator needs usage as it is used by the inspector in testing
GRANT USAGE ON SCHEMA auth, audit, fltr, {settings.DB_SCHEMA} TO {settings.DB_SCHEMA}_authenticator, {settings.DB_SCHEMA}_admin, {settings.DB_SCHEMA}_reader, {settings.DB_SCHEMA}_writer;

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth, audit, fltr, {settings.DB_SCHEMA} TO {settings.DB_SCHEMA}_authenticator, {settings.DB_SCHEMA}_admin, {settings.DB_SCHEMA}_writer;

GRANT SELECT ON ALL TABLES IN SCHEMA auth, audit, fltr, {settings.DB_SCHEMA} TO {settings.DB_SCHEMA}_reader;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit, auth, fltr, {settings.DB_SCHEMA} TO {settings.DB_SCHEMA}_writer;
GRANT SELECT, INSERT, UPDATE ON TABLE audit.meta TO {settings.DB_SCHEMA}_writer, {settings.DB_SCHEMA}_admin;
REVOKE UPDATE (id, created_at) ON TABLE audit.meta FROM public;
REVOKE UPDATE ON ALL TABLES IN SCHEMA audit FROM public;

"""


SET_SEARCH_PATHS = f"""
-- Set the search path for the DB_OWNER
ALTER ROLE {settings.DB_SCHEMA}_base_role SET search_path TO audit, auth, fltr, {settings.DB_SCHEMA};
ALTER ROLE {settings.DB_SCHEMA}_reader SET search_path TO audit, auth, fltr, {settings.DB_SCHEMA};
ALTER ROLE {settings.DB_SCHEMA}_writer SET search_path TO audit, auth, fltr, {settings.DB_SCHEMA};
ALTER ROLE {settings.DB_SCHEMA}_admin SET search_path TO audit, auth, fltr, {settings.DB_SCHEMA};
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


CREATE_UPDATE_META_RECORD_FUNCTION = """
/*
Simple function to update a meta record when it's "parent" record is updated.
*/

CREATE OR REPLACE FUNCTION audit.update_meta_record() RETURNS TRIGGER AS $$
BEGIN
    UPDATE audit.meta SET modified_at=now() WHERE id=OLD.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_IS_SUPERUSER_FUNCTION = """
/* simple function to check if a user is a superuser */
CREATE OR REPLACE FUNCTION auth.is_superuser(VARCHAR(26)) RETURNS BOOLEAN AS $$
SELECT is_superuser FROM auth.user WHERE id = $1;
$$ language sql;
"""

CREATE_IS_CUSTOMER_ADMIN_FUNCTION = """
/* simple function to check if a user is a customer_admin */
CREATE OR REPLACE FUNCTION auth.is_customer_admin(VARCHAR(26)) RETURNS BOOLEAN AS $$
SELECT is_customer_admin FROM auth.user WHERE id = $1;
$$ language sql;
"""


def update_meta_trigger(table_name: str):
    _table_name = table_name.replace(".", "_")
    return f"""
        -- Create the update_meta trigger for the table
        CREATE OR REPLACE TRIGGER {_table_name}_update_meta_trigger
            AFTER UPDATE 
            ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION audit.update_meta_record();
    """


def enable_rls(schema_name: str, table_name: str):
    return f"""
        -- Enable RLS for the table
        ALTER TABLE {schema_name}.{table_name} ENABLE ROW LEVEL SECURITY;
    """


def enable_auditing(table_name: str):
    return f"""
        -- Enable auditing for the table
        SELECT audit.audit_table('{table_name}');
    """


'''
# PROBABLY NOT NEEDED

CREATE_LOGIN_VIEW = """
    /*
    View for users to login with
    */

    CREATE OR REPLACE VIEW auth.login_view AS
    SELECT u.id,
           u.email,
           h.hashed_password,
           m.is_active,
           a.is_locked,
           a.is_suspended
    FROM auth.user u
        INNER JOIN auth.hashed_password h
            ON h.id=u.id
        INNER JOIN audit.meta m
            ON m.id=u.id
        INNER JOIN auth.user_admin a
            ON a.id=u.id;
"""
'''
