from config import settings  # type: ignore


CREATE_CAN_INSERT_GROUP_FUNCTION = f"""
CREATE OR REPLACE FUNCTION auth.can_insert_group(customerid VARCHAR(26))
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS $$
DECLARE
    group_count INT4;
    customertype auth.customertype;
BEGIN
    SELECT customer_type INTO customertype
    FROM auth.customer
    WHERE id = customerid;

    SELECT COUNT(*) INTO group_count
    FROM auth.group
    WHERE customer_id = customerid;

    IF customertype = 'INDIVIDUAL' AND
        {settings.MAX_INDIVIDUAL_GROUPS} > 0 AND
        group_count >= {settings.MAX_INDIVIDUAL_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'SMALL_BUSINESS' AND
        {settings.MAX_SMALL_BUSINESS_GROUPS} > 0 AND
        group_count >= {settings.MAX_SMALL_BUSINESS_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'CORPORATE' AND
        {settings.MAX_CORPORATE_GROUPS} > 0 AND
        group_count >= {settings.MAX_CORPORATE_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'ENTERPRISE' AND
        {settings.MAX_ENTERPRISE_GROUPS} > 0 AND
        group_count >= {settings.MAX_ENTERPRISE_GROUPS} THEN
            RETURN false;
    END IF;
    RETURN true;
END
$$;
"""

CREATE_GROUP_FOR_CUSTOMER_FUNCTION = """
/*
Function to create a new Group record when a new Customer is inserted.
The Group record is created with the same name as the Customer.
Deleted automatically by the DB via the FK Constraints ondelete when an group is deleted.
*/
CREATE OR REPLACE FUNCTION auth.group_for_customer_function()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_group_id VARCHAR(26);
    new_role_id VARCHAR(26);
    new_group_permission_id VARCHAR(26); 
BEGIN
    IF auth.can_insert_group(NEW.id) = true THEN
        INSERT INTO auth.group(customer_id, name)
            VALUES (NEW.id, NEW.name) returning id into new_group_id;

        INSERT INTO auth.role(customer_id, name, description)
            VALUES (NEW.id,  NEW.name || ' Admin', 'Admin Role') returning id into new_role_id;

        SELECT id from auth.group_permission
            WHERE group_id = new_group_id AND name = 'Admin'
            INTO new_group_permission_id;

        INSERT INTO auth.role__group_permission(role_id, group_permission_id)
            VALUES (new_role_id, new_group_permission_id);
    END IF;
    RETURN NEW;
END;
$$
"""

CREATE_GROUP_FOR_CUSTOMER_TRIGGER = """
-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER group_for_customer_trigger
    AFTER INSERT ON auth.customer
    FOR EACH ROW
    EXECUTE FUNCTION auth.group_for_customer_function();
"""

CREATE_GROUP_PERMISSION_FUNCTION = """
/*
Function to create a new GroupPermission record when a new Group is inserted.
group_permissions record created for each group with the following combinations of permissions:
    [READ]
    [READ, CREATE]
    [READ, CREATE, UPDATE]
    [READ, CREATE, DELETE]
    [READ, CREATE, UPDATE, DELETE]
    [READ, UPDATE]
    [READ, UPDATE, DELETE]
    [READ, DELETE]
    Deleted automatically by the DB via the FK Constraints ondelete when an group is deleted.
*/
CREATE OR REPLACE FUNCTION auth.group_permission_function()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ']::auth.permission[], 'Read Only');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'CREATE']::auth.permission[], 'Read and Create');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'CREATE', 'UPDATE']::auth.permission[], 'Read, Create, Update');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'CREATE', 'DELETE']::auth.permission[], 'Read, Create, Delete');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'CREATE', 'UPDATE', 'DELETE']::auth.permission[], 'Admin');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'UPDATE']::auth.permission[], 'Read and Update');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'UPDATE', 'DELETE']::auth.permission[], 'Read, Update, Delete');
    INSERT INTO auth.group_permission(group_id, permissions, name)
        VALUES (NEW.id, ARRAY['READ', 'DELETE']::auth.permission[], 'Read and Delete');
    RETURN NEW;
END;
$$
"""

CREATE_GROUP_PERMISSION_TRIGGER = """
-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER group_permission_trigger
    AFTER INSERT ON auth.group
    FOR EACH ROW
    EXECUTE FUNCTION auth.group_permission_function();
"""

CREATE_GET_ALL_PERMISSIBLE_GROUPS_FUNCTION = """
CREATE OR REPLACE FUNCTION auth.get_all_permissible_groups(use_parent VARCHAR)
    RETURNS VARCHAR[]
    LANGUAGE plpgsql
AS $$
DECLARE
    process_parents VARCHAR[] := ARRAY[ use_parent ];
    children VARCHAR[] := '{}';
    new_children VARCHAR[];
BEGIN
    children := ARRAY( SELECT id FROM auth.group WHERE id = use_parent );
    WHILE ( array_upper( process_parents, 1 ) IS NOT NULL ) LOOP
        new_children := ARRAY( SELECT id FROM auth.group WHERE parent_id = ANY( process_parents )
            AND id <> ALL( children ) );
        children := children || new_children;
        process_parents := new_children;
    END LOOP;
    RETURN children;
END;
$$;
"""
