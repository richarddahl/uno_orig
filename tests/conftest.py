'''
import pytest
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.DB_URL)


@pytest.fixture
def db_connection(engine):
    """Returns an sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    yield connection

    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


@pytest.fixture(scope="session")
async def async_engine():
    return create_async_engine(settings.DB_URL)
'''


import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from uno.base import Base  # type: ignore
from commands.create_db import create_db  # type: ignore
from commands.drop_db import drop_db  # type: ignore

from config import settings


Session = sessionmaker()
engine = create_engine(f"{settings.DB_URL}_test", echo=False)


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> None:
    """
    Add all of the tables/views/etc. into the DB before running anything.
    """
    drop_db(testing=True)
    create_db(testing=True)


@pytest.fixture
def db_connection():
    """Returns an sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()

    # begin the nested transaction
    transaction = connection.begin()

    yield connection

    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()
