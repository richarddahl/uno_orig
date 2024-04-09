# Role Based Access Control (RBAC)

The uno RBAC leverages a simple structure, enforced by the database through Check Constraints, Functions, Triggers, and Row Level Security Policies, to ensure only authorized users may access database records.

## RLS Policies

There are three distinct policies applied to all configured tables.  Each is described in detail below.

### Superuser

All user defined with `is_superuser=True` (superusers) have INSERT, SELECT, UPDATE, and DELETE (full control) access to all database tables.

NOTE: superusers are not associated with a customer, and have no roles assigned to them.  Attempting to create a user with a customer_id and `is_superuser=True` will raise an error as will attempting to associate a superuser with a Role.

### Customer Administrator

All users defined with `is_customer_admin=True` users have the following authoriziations:

- INSERT, SELECT, UPDATE, and DELETE (full control) access to all database objects associated with thier customer
- INSERT and UPDATE Role objects associated with thier customer
- INSERT users assocatied with thier customer and UPDATE those user's roles.

### Unprivileged Customer Users

All users defined with `is_customer_admin=False` (unpriviled users) have the following authorizations:

- UPDATE the following columns of thier user record:  
    - email_address, handle, and full_name  
-  Access other objects as defined in thier role  

## Role

## Group

## Group Permission

## Customer

## User

