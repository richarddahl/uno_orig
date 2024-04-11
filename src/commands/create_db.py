from __future__ import annotations

from alembic.config import Config
from alembic import command

from sqlalchemy import create_engine, text  # type: ignore
from sqlalchemy.exc import ProgrammingError

from sql.pysql.base_sql import (
    CREATE_ROLES,
    CREATE_SCHEMAS,
    SET_SEARCH_PATHS,
    REVOKE_ACCESS,
    CONFIGURE_PRIVILEGES,
    CREATE_INSERT_META_RECORD_FUNCTION,
    CREATE_UPDATE_META_RECORD_FUNCTION,
    CREATE_IS_SUPERUSER_FUNCTION,
    CREATE_IS_CUSTOMER_ADMIN_FUNCTION,
    create_database,
    update_meta_trigger,
    enable_rls,
)  # type: ignore

from sql.pysql.group_sql import (
    CREATE_GROUP_FOR_CUSTOMER_FUNCTION,
    CREATE_GROUP_FOR_CUSTOMER_TRIGGER,
    CREATE_GROUP_PERMISSION_FUNCTION,
    CREATE_GROUP_PERMISSION_TRIGGER,
    CREATE_GET_ALL_PERMISSIBLE_GROUPS_FUNCTION,
    CREATE_CAN_INSERT_GROUP_FUNCTION,
)  # type: ignore

from uno.base import Base
from config import settings  # type: ignore


DB_AUDITED_TABLES = [
    "auth.user",
    "auth.group",
    "auth.customer",
    "auth.role",
    "fltr.field",
    "fltr.filter",
    "fltr.query",
    "auth.role__group_permission",
    "auth.user__role",
    "fltr.query__filter",
    "fltr.query__subquery",
]


def create_db(testing: bool = False):
    """
    Create the database and its schema, owner, and API user.
    Intentially not using the async engine as we need to create the database and users.
    Intentially not catching else: #except:ions as we want to see the errors.
    """

    # Connect to the postgres database as the postgres user
    db_name = f"{settings.DB_NAME}_test" if testing is True else settings.DB_NAME

    eng = create_engine(f"{settings.DB_DRIVER}://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("")
        print(
            f"Creating the db: {db_name}, and all the roles, users, and schema for the application."
        )
        conn.execute(text("SET pgaudit.log = 'all';"))
        conn.execute(text("SET pgaudit.log_relation = on;"))
        conn.execute(text("SET pgaudit.log_line_prefix = '%m %u %d [%p]: ';"))

        try:
            # Create the roles
            print("Creating the roles")
            conn.execute(text(CREATE_ROLES))
        except ProgrammingError:
            print("Roles already exist")

        try:
            # Create the database
            print("Creating the database")
            conn.execute(text(create_database(db_name)))
        except ProgrammingError:
            print("Database already exists")

        conn.close()
    eng.dispose()

    # Connect to the new database as the postgres user
    print("")
    print(
        """
        Connecting to new database creating the schemas, functions, and triggers, and 
        setting the privileges and search paths."
        """
    )
    eng = create_engine(
        f"{settings.DB_DRIVER}://postgres@/{db_name}",
        echo=False,
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try:
            # Create the schemas
            print("Creating the schemas")
            conn.execute(text(CREATE_SCHEMAS))
        except ProgrammingError:
            print("Schemas already exist")

        # Revoke access to the schemas
        print("Revoking public access to schemas")
        conn.execute(text(REVOKE_ACCESS))

        # Set search paths
        print("Setting role search paths")
        conn.execute(text(SET_SEARCH_PATHS))
        print("")

        with open("src/sql/pgulid.sql", "r") as f:
            CREATE_PGULID = f.read()
        f.close()
        try:
            conn.execute(text("SET SESSION search_path TO audit"))
            print("Creating the pgulid function")
            conn.execute(text(CREATE_PGULID))
        except ProgrammingError:
            print("pgulid function already exists")

        try:
            print("Creating the insert meta record function")
            conn.execute(text(CREATE_INSERT_META_RECORD_FUNCTION))
        except ProgrammingError:
            print("insert_meta_record function already exists")

        try:
            print("Creating the update meta record function")
            conn.execute(text(CREATE_UPDATE_META_RECORD_FUNCTION))
        except ProgrammingError:
            print("update_meta_record function already exists")

        print("Creating the btree_gist extension")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgaudit;"))
        conn.execute(text("CREATE EXTENSION supa_audit CASCADE;"))

        conn.close()

    eng.dispose()

    if testing is True:
        alembic_cfg = Config("./alembic.ini", ini_section="alembic-test")
    else:
        alembic_cfg = Config("./alembic.ini")
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Initial Revision",
        )
    command.upgrade(alembic_cfg, "head")

    eng = create_engine(
        # f"{settings.DB_DRIVER}://{settings.DB_SCHEMA}_authenticator@/{db_name}",
        f"{settings.DB_DRIVER}://postgres@/{db_name}",
        echo=False,
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(
            text(f"SET SESSION search_path TO audit, auth, fltr, {settings.DB_SCHEMA}")
        )

        try:
            # Grant necessary access to the schemas
            print("")
            print("Configuring privileges for the schemas")
            conn.execute(text(CONFIGURE_PRIVILEGES))
        except Exception as e:
            print(e)
            print("")

        conn.execute(text(f"SET ROLE {settings.DB_SCHEMA}_admin;"))
        print("Creating the can_insert_group function")
        conn.execute(text(CREATE_CAN_INSERT_GROUP_FUNCTION))
        conn.execute(
            text(
                """
                ALTER TABLE auth.group ADD CONSTRAINT ck_can_insert_group
                CHECK (auth.can_insert_group(customer_id));
                """
            )
        )

        print("")
        print("Creating Group and Group Permission functions and triggers")
        conn.execute(text(CREATE_GROUP_FOR_CUSTOMER_FUNCTION))
        conn.execute(text(CREATE_GROUP_FOR_CUSTOMER_TRIGGER))
        conn.execute(text(CREATE_GROUP_PERMISSION_FUNCTION))
        conn.execute(text(CREATE_GROUP_PERMISSION_TRIGGER))
        conn.execute(text(CREATE_IS_SUPERUSER_FUNCTION))
        conn.execute(text(CREATE_IS_CUSTOMER_ADMIN_FUNCTION))
        conn.execute(text(CREATE_GET_ALL_PERMISSIBLE_GROUPS_FUNCTION))

        for table_name in DB_AUDITED_TABLES:
            table = Base.metadata.tables[table_name]
            print(f"Enabling AUDITING for {table_name}")
            try:
                conn.execute(
                    text(f"SELECT audit.enable_tracking('{table_name}'::regclass);")
                )

                for fk_constraint in table.foreign_key_constraints:
                    if fk_constraint.referred_table.name == "meta":
                        conn.execute(text(update_meta_trigger(table_name)))
            except Exception as e:
                print(e)
                print("")
        for table_name in settings.DB_AUDITED_TABLES:
            table = Base.metadata.tables[table_name]
            print(f"Enabling AUDITING for {table_name}")
            try:
                conn.execute(
                    text(f"SELECT audit.enable_tracking('{table_name}'::regclass);")
                )

                for fk_constraint in table.foreign_key_constraints:
                    if fk_constraint.referred_table.name == "meta":
                        conn.execute(text(update_meta_trigger(table_name)))
            except Exception as e:
                print(e)
                print("")

        conn.close()
    eng.dispose()
    print("")
    print("Database created")
    print("")


if __name__ == "__main__":
    create_db()
