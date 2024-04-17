from sqlalchemy import Table


def create_graph_nodes_and_edges(table: Table):
    for column in table.columns:
        print(column)
    print("")


def create_graph_function(table: Table):
    table_name = table.name
    schema_name = table.schema
    graph_name = table.info.get("graph", table.info.get("association_graph", None))
    if not graph_name:
        raise ValueError(f"Table {table_name} does not have a graph specified.")
    edge_columns = []
    node_attribute_columns = []
    for column in table.columns:
        if column.foreign_keys:
            edge_columns.append(column)
        else:
            node_attribute_columns.append(column)
    return f"""
        CREATE OR REPLACE FUNCTION {schema_name}.{table_name}_create_graph_node()
            RETURNS TRIGGER
            LANGUAGE plpgsql
        AS $$
        BEGIN 
            SELECT *
            FROM ag_catalog.cypher('{graph_name}', $$
                CREATE ('{table_name}': '{table_name}')
            $$) as (v ag_catalog.agtype);
        END
        $$
    """


def create_graph_trigger(table: Table):
    table_name = table.name
    schema_name = table.schema
    return f"""
        CREATE OR REPLACE TRIGGER {schema_name}.{table_name}_create_graph_node_trigger
            AFTER INSERT, UPDATE, DELETE
            ON {schema_name}.{table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {schema_name}.{table_name}_create_graph_node();
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
