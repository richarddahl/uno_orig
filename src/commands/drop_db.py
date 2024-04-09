from __future__ import annotations

import os
import glob

from sqlalchemy import create_engine, text  # type: ignore

from uno.base import meta_data
from config import settings
from sql.pysql.base_sql import (
    drop_database,
    DROP_ROLES,
)  # type: ignore


def drop_db(testing: bool = False):
    """
    Create the database and its schema, owner, and API user.
    Intentially not using the async engine as we need to create the database and users.
    Intentially not catching else: #except:ions as we want to see the errors.
    """
    if testing is False:
        for file in glob.glob("alembic/versions/*.py", root_dir=os.curdir):
            os.remove(file)
        for file in glob.glob("alembic/versions/__pycache__/*.pyc", root_dir=os.curdir):
            os.remove(file)
    # Connect to the postgres database as the postgres user
    eng = create_engine("postgresql+psycopg://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("")
        print(
            f"Dropping the db: {settings.DB_NAME}{'_test' if testing else ''}, and all the roles, users, and schema for the application."
        )

        # Drop the existing objects
        conn.execute(text(drop_database(f"{settings.DB_NAME}_test")))
        if testing is False:
            conn.execute(text(drop_database(settings.DB_NAME)))
            conn.execute(text(DROP_ROLES))
        conn.close()
    eng.dispose()


if __name__ == "__main__":
    drop_db()
