import datetime
from typing import Optional

from sqlalchemy.sql import func, text
from sqlalchemy.dialects.postgresql import (
    VARCHAR,
    ENUM,
)
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy import Table, Column
from sqlalchemy import (
    ForeignKey,
    FetchedValue,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uno.enumerations import (
    ColumnSecurity,
    FieldType,
    Include,
    Match,
    Lookup,
)
from uno.utilities import set_group_id, set_owner_id  # type: ignore
from uno.base import Base, str_26, str_255, decimal
from uno.auth.models import User, Group
from uno.audit.models import Meta


class Field(Base):
    __tablename__ = "field"
    __table_args__ = (
        UniqueConstraint("table_name", "field_name"),
        {
            "schema": "fltr",
            "comment": "Describes a column in a db table.",
            "info": {"vertex": True, "audited": True},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=func.audit.insert_meta_record(),
        server_onupdate=FetchedValue(),
        info={"graph_property": True},
    )
    table_name: Mapped[str_255] = mapped_column(index=True)
    field_name: Mapped[str_255] = mapped_column()
    label: Mapped[str_255] = mapped_column()
    field_type: Mapped[FieldType] = mapped_column(
        ENUM(
            FieldType,
            name="fieldtype",
            create_type=True,
            schema="fltr",
        ),
    )
    includes: Mapped[list[Include]] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="fltr",
        )
    )
    matches: Mapped[list[Match]] = mapped_column(
        ENUM(
            Match,
            name="match",
            create_type=True,
            schema="fltr",
        )
    )
    lookups: Mapped[list[Lookup]] = mapped_column(
        ENUM(
            Lookup,
            name="lookup",
            create_type=True,
            schema="fltr",
        )
    )
    column_security: Mapped[ColumnSecurity] = mapped_column(
        ENUM(
            ColumnSecurity,
            name="columsecurity",
            create_type=True,
            schema="fltr",
        ),
        default=ColumnSecurity.PUBLIC,
    )

    # Relationships
    meta: Mapped[Meta] = relationship()
    filters: Mapped[list["Filter"]] = relationship(back_populates="field")

    # AssociationProxies
    is_active: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_active"
    )
    is_deleted: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_deleted"
    )
    created_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="created_at"
    )
    modified_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="modified_at"
    )


class Filter(Base):
    __tablename__ = "filter"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "field_id",
            "lookup",
            "include",
            "match",
            "bigint_value",
            "boolean_value",
            "date_value",
            "decimal_value",
            "related_table",
            "related_id",
            "string_value",
            "text_value",
            "time_value",
            "timestamp_value",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_filter__unique_together",
            "group_id",
            "field_id",
            "lookup",
            "include",
            "match",
        ),
        CheckConstraint(
            """
                bigint_value IS NOT NULL
                OR boolean_value IS NOT NULL
                OR date_value IS NOT NULL
                OR decimal_value IS NOT NULL
                OR related_id IS NOT NULL AND related_table IS NOT NULL
                OR text_value IS NOT NULL
                OR time_value IS NOT NULL
                OR timestamp_value IS NOT NULL
            """,
            name="ck_filter_value",
        ),
        CheckConstraint(
            """
                related_id IS NOT NULL AND related_table IS NOT NULL
                OR related_id IS NULL AND related_table IS NULL
            """,
            name="ck_related_object",
        ),
        {
            "schema": "fltr",
            "comment": "A db column bound to a value.",
            "info": {"vertex": True, "audited": True},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=func.audit.insert_meta_record(),
        server_onupdate=FetchedValue(),
        info={"graph_property": True},
    )
    user_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        index=True,
        default=set_owner_id,
        info={"edge": "CREATED_BY"},
    )
    group_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.group.id", ondelete="CASCADE"),
        index=True,
        default=set_group_id,
        info={"edge": "ACCESSIBLE_BY"},
    )
    field_id: Mapped[str_26] = mapped_column(
        ForeignKey("fltr.field.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "FILTERS_DATA_FROM"},
    )
    lookup: Mapped[Lookup] = mapped_column(
        ENUM(
            Lookup,
            name="lookup",
            create_type=True,
            schema="fltr",
        ),
        insert_default=Lookup.EQUAL,
    )
    include: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="fltr",
        ),
        insert_default=Include.INCLUDE,
    )
    match: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="fltr"),
        insert_default=Match.AND,
    )
    bigint_value: Mapped[Optional[int]] = mapped_column()
    boolean_value: Mapped[Optional[bool]] = mapped_column()
    date_value: Mapped[Optional[datetime.date]] = mapped_column()
    decimal_value: Mapped[Optional[decimal]] = mapped_column()
    related_table: Mapped[Optional[str_255]] = mapped_column()
    related_id: Mapped[Optional[str_26]] = mapped_column()
    string_value: Mapped[Optional[str_255]] = mapped_column()
    text_value: Mapped[Optional[str]] = mapped_column()
    time_value: Mapped[Optional[datetime.time]] = mapped_column()
    timestamp_value: Mapped[Optional[datetime.datetime]] = mapped_column()

    # Relationships
    meta: Mapped[Meta] = relationship()
    user: Mapped["User"] = relationship(back_populates="filters")
    group: Mapped["Group"] = relationship(back_populates="filters")
    field: Mapped["Field"] = relationship(back_populates="filters")

    # AssociationProxies
    is_active: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_active"
    )
    is_deleted: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_deleted"
    )
    created_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="created_at"
    )
    modified_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="modified_at"
    )


class Query(Base):
    __tablename__ = "query"
    __table_args__ = (
        UniqueConstraint("group_id", "name"),
        Index("ix_group_id_name_user_query", "group_id", "name"),
        {
            "schema": "fltr",
            "comment": "Filter queries",
            "info": {"vertex": True, "audited": True},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=func.audit.insert_meta_record(),
        server_onupdate=FetchedValue(),
        info={"graph_property": True},
    )
    user_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        index=True,
        default=set_owner_id,
        info={"edge": "CREATED_BY"},
    )
    group_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.group.id", ondelete="CASCADE"),
        index=True,
        default=set_group_id,
        info={"edge": "ACCESSIBLE_BY"},
    )
    name: Mapped[str_255] = mapped_column()
    object_type: Mapped[str_255] = mapped_column()
    show_with_object: Mapped[bool] = mapped_column(server_default=text("false"))
    include_values: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="fltr",
        ),
        insert_default=Include.INCLUDE,
    )
    match_values: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="fltr"),
        insert_default=Match.AND,
    )
    include_subqueries: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="fltr",
        ),
        insert_default=Include.INCLUDE,
    )
    match_subqueries: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="fltr"),
        insert_default=Match.AND,
    )

    # Relationships
    meta: Mapped[Meta] = relationship()
    user: Mapped["User"] = relationship(back_populates="queries")
    group: Mapped["Group"] = relationship(back_populates="queries")

    # AssociationProxies
    is_active: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_active"
    )
    is_deleted: AssociationProxy[bool] = association_proxy(
        target_collection="meta", attr="is_deleted"
    )
    created_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="created_at"
    )
    modified_at: AssociationProxy[datetime.datetime] = association_proxy(
        target_collection="meta", attr="modified_at"
    )


query_filter = Table(
    "query__filter",
    Base.metadata,
    Column(
        "query_id",
        VARCHAR(26),
        ForeignKey("fltr.query.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        info={"start_vertex": "Query"},
    ),
    Column(
        "filter_id",
        VARCHAR(26),
        ForeignKey("fltr.filter.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        info={"end_vertex": "Filter"},
    ),
    schema="fltr",
    info={"edge": "HAS_FILTER", "audited": True},
)

query_subquery = Table(
    "query__subquery",
    Base.metadata,
    Column(
        "query_id",
        VARCHAR(26),
        ForeignKey("fltr.query.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        info={"start_vertex": "Query"},
    ),
    Column(
        "subquery_id",
        VARCHAR(26),
        ForeignKey("fltr.query.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        info={"end_vertex": "Query"},
    ),
    schema="fltr",
    info={"edge": "HAS_SUBQUERY", "audited": True},
)
