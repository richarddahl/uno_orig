import datetime

from sqlalchemy import Table, Column


from config import settings


def get_column_type(column: Column) -> str:
    if issubclass(column.type.python_type, list):
        return f"to_jsonb(NEW.{column.name})"
    if issubclass(column.type.python_type, str):
        return f"quote_nullable(NEW.{column.name}::{column.type})"
    if issubclass(column.type.python_type, bool):
        return f"quote_nullable(NEW.{column.name})"
    if issubclass(column.type.python_type, int):
        return f"quote_nullable(NEW.{column.name}::{column.type})"
    if issubclass(column.type.python_type, datetime.datetime):
        return f"quote_nullable(NEW.{column.name}::{column.type})"
    return f"quote_nullable(NEW.{column.name}::{column.type})"


def create_insert_edge_function(table: Table):
    table_name = table.name
    schema_name = table.schema
    start_vertex = []
    end_vertex = []
    for column in table.columns:
        if column.info.get("start_vertex", False) is True:
            for fk in column.foreign_keys:
                start_vertex = [
                    fk.column.table.name.title(),
                    get_column_type(column),
                ]
                break
        if column.info.get("end_vertex", False) is True:
            for fk in column.foreign_keys:
                end_vertex = [
                    fk.column.table.name.title(),
                    get_column_type(column),
                ]
                break
    func = f"""
        /*
        Function to create a new edge record when a new {schema_name}.{table_name} 
        association table record is inserted.  Uses the table.info['edge'] property to
        determine the edge label and the start_vertex and end_vertex properties to determine
        the vertices to connect.
        */
        CREATE OR REPLACE FUNCTION {schema_name}.{table_name}_insert_edge()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        VOLATILE
        AS $BODY$
        BEGIN
            SET ROLE {settings.DB_SCHEMA}_admin;
            LOAD '$libdir/plugins/age.dylib';
            SET search_path TO ag_catalog, auth, fltr, {settings.DB_SCHEMA};
            EXECUTE format('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{start_vertex[0]} {{id: %s}})
                MATCH (w:{end_vertex[0]} {{id: %s}})
                CREATE (v)-[a:{table.info.get("edge")}]->(w)
            $$) AS (a agtype);', {start_vertex[1]}, {end_vertex[1]});
            RETURN NEW;
        END
        $BODY$;
    """
    return func


def create_insert_edge_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_insert_edge_trigger
            AFTER INSERT
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {schema_name}.{table_name}_insert_edge();
    """


def create_insert_vertex_function(table: Table):
    table_name = table.name
    schema_name = table.schema

    edges = []
    for column in table.columns:
        if column.info.get("edge", False) is not False:
            for fk in column.foreign_keys:
                edges.append(
                    (
                        table_name.title(),
                        fk.column.table.name.title(),
                        column.info.get("edge"),
                        get_column_type(table.columns["id"]),
                        get_column_type(column),
                    )
                )
    edge_creation_statements = " ".join(
        [
            f"""
            EXECUTE format('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{edge[0]} {{id: %s}})
                MATCH (w:{edge[1]} {{id: %s}})
                CREATE (v)-[e:{edge[2]}]->(w)
            $$) AS (e agtype);', {edge[3]}, {edge[4]});
            """
            for edge in edges
        ]
    )
    property_names = ", ".join(
        [
            f"{column.name}: %s"
            for column in table.columns
            if not column.info.get("edge")
            and column.info.get("graph_property", True) is True
        ]
    )
    property_values = ", ".join(
        [
            get_column_type(column)
            for column in table.columns
            if not column.info.get("edge", False)
            and column.info.get("graph_property", True) is True
        ]
    )
    func = f"""
        CREATE OR REPLACE FUNCTION {schema_name}.{table_name}_insert_vertex()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        VOLATILE
        AS $BODY$
        BEGIN
            SET ROLE {settings.DB_SCHEMA}_admin;
            LOAD '$libdir/plugins/age.dylib';
            SET search_path TO ag_catalog, auth, fltr, {settings.DB_SCHEMA};
            EXECUTE format('SELECT * FROM cypher(''graph'', $$
                CREATE (v:{table_name.title()} {{{property_names}}})
            $$) AS (a agtype);', {property_values});
            {edge_creation_statements}
            RETURN NEW;
        END
        $BODY$;
    """
    return func


def create_insert_vertex_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_insert_vertex_trigger
            AFTER INSERT
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {schema_name}.{table_name}_insert_vertex();
    """


def create_update_graph_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_update_graph_trigger
            AFTER UPDATE
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {schema_name}.{table_name}_update_graph();
    """


def create_delete_graph_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {table_name}_delete_graph_trigger
            AFTER DELETE
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {schema_name}.{table_name}_delete_graph();
    """
