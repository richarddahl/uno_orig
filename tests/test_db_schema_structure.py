from __future__ import annotations

import pytest

from sqlalchemy import inspect

from config import settings  # type: ignore

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_db_structure(db_connection):
    db_inspector = inspect(db_connection)
    assert "public" in db_inspector.get_schema_names()
    assert "audit" in db_inspector.get_schema_names()
    assert "auth" in db_inspector.get_schema_names()
    assert "fltr" in db_inspector.get_schema_names()
    assert settings.DB_SCHEMA in db_inspector.get_schema_names()


@pytest.mark.asyncio
async def test_audit_schema_structure(db_connection):
    db_inspector = inspect(db_connection)
    reflected_table_names = db_inspector.get_table_names(schema="audit")
    # for table_name in settings.DB_AUDITED_TABLES:
    #    assert f"{table_name.replace('.', '_')}" in reflected_table_names

    for table_name in [
        "alembic_version",
        "meta",
        "access_log",
        "auth_user",
        "auth_customer",
        "auth_group",
        "auth_role",
        # "auth_role__group_permission",
        # "auth_user__role",
        "fltr_field",
        "fltr_filter",
        "fltr_query",
        # "fltr_query__filter",
        # "fltr_query__subquery",
    ]:
        assert table_name in reflected_table_names

    for reflected_table_name in reflected_table_names:
        assert reflected_table_name in [
            "alembic_version",
            "meta",
            "access_log",
            "auth_user",
            "auth_customer",
            "auth_group",
            "auth_role",
            # "auth_role__group_permission",
            # "auth_user__role",
            "fltr_field",
            "fltr_filter",
            "fltr_query",
            # "fltr_query__filter",
            # "fltr_query__subquery",
        ]


@pytest.mark.asyncio
async def test_auth_schema_structure(db_connection):
    db_inspector = inspect(db_connection)
    reflected_table_names = db_inspector.get_table_names(schema="auth")
    for table_name in [
        "customer",
        "group",
        "group_permission",
        "role",
        "user",
        "hashed_password",
        "role__group_permission",
        "user__role",
    ]:
        assert table_name in reflected_table_names


@pytest.mark.asyncio
async def test_fltr_schema_structure(db_connection):
    db_inspector = inspect(db_connection)
    reflected_table_names = db_inspector.get_table_names(schema="fltr")
    for table_name in [
        "field",
        "filter",
        "query",
        "query__filter",
        "query__subquery",
    ]:
        assert table_name in reflected_table_names
