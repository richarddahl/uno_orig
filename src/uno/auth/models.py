import datetime
from typing import Optional, Dict

from sqlalchemy import Table, Column
from sqlalchemy.sql import func, text
from sqlalchemy.dialects.postgresql import (
    ENUM,
    VARCHAR,
    ARRAY,
    BIGINT,
)
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy import (
    ForeignKey,
    Index,
    Identity,
    FetchedValue,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.orm.collections import attribute_keyed_dict

from uno.enumerations import CustomerType, Permission
from uno.base import Base, str_26, str_128, str_255
from uno.audit.models import Meta, AccessLog


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(
            """
                is_superuser = 'true' AND customer_id IS NULL OR
                is_customer_admin = 'true' AND customer_id IS NOT NULL OR
                is_superuser = 'false' AND is_customer_admin = 'false' AND customer_id IS NOT NULL
            """,
            name="ck_user_is_superuser_and_not_customer_admin",
        ),
        {
            "schema": "auth",
            "comment": "Application end-users",
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
    email: Mapped[str_255] = mapped_column(unique=True)
    handle: Mapped[str_255] = mapped_column(unique=True)
    full_name: Mapped[str_255] = mapped_column()
    customer_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("auth.customer.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WORKS_FOR_CUSTOMER"},
    )
    is_superuser: Mapped[bool] = mapped_column(server_default=text("false"))
    is_customer_admin: Mapped[bool] = mapped_column(server_default=text("false"))
    is_verified: Mapped[bool] = mapped_column(
        server_default=text("false"), info={"graph_property": False}
    )
    is_locked: Mapped[bool] = mapped_column(
        server_default=text("false"), info={"graph_property": False}
    )
    is_suspended: Mapped[bool] = mapped_column(
        server_default=text("false"), info={"graph_property": False}
    )
    suspension_expiration: Mapped[Optional[datetime.datetime]] = mapped_column(
        info={"graph_property": False}
    )

    # Relationships
    meta: Mapped["Meta"] = relationship()
    customer: Mapped["Customer"] = relationship(back_populates="users")
    hashed_password: Mapped["HashedPassword"] = relationship(back_populates="user")
    access_logs: Mapped[list["AccessLog"]] = relationship(back_populates="user")
    roles: Mapped[list["Role"]] = relationship(
        secondary="auth.user__role", back_populates="users"
    )
    filters: Mapped[list["Filter"]] = relationship(back_populates="user")
    queries: Mapped[list["Query"]] = relationship(back_populates="user")

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


class HashedPassword(Base):
    __tablename__ = "hashed_password"
    __table_args__ = (
        {
            "schema": "auth",
            "comment": "Application end-user hashed passwords",
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        primary_key=True,
    )
    hashed_password: Mapped[str_128] = mapped_column()
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(),
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="hashed_password")

    # AssociationProxies
    email: AssociationProxy[str_255] = association_proxy(
        target_collection="user", attr="email"
    )
    handle: AssociationProxy[str_255] = association_proxy(
        target_collection="user", attr="handle"
    )


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        {
            "schema": "auth",
            "comment": "Application end-user customers",
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
    name: Mapped[str_255] = mapped_column(unique=True)
    customer_type: Mapped[CustomerType] = mapped_column(
        ENUM(CustomerType, name="customertype", create_type=True, schema="auth"),
        server_default=CustomerType.INDIVIDUAL.name,
    )

    # Relationships
    meta: Mapped[Meta] = relationship()
    users: Mapped[list[User]] = relationship(back_populates="customer")
    groups: Mapped[list["Group"]] = relationship(back_populates="customer")
    roles: Mapped[list["Role"]] = relationship(back_populates="customer")

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


class Group(Base):
    __tablename__ = "group"
    __table_args__ = (
        UniqueConstraint("customer_id", "name", name="uq_group_customer_id_name"),
        {
            "schema": "auth",
            "comment": "Application end-user groups, child groups can be created for granular access control",
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
    customer_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.customer.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IDENTIFIES_DATA_AS_BELONGING_TO_CUSTOMER"},
    )
    parent_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("auth.group.id", ondelete="SET NULL"),
        index=True,
        info={"edge": "IS_A_CHILD_OF_GROUP"},
    )
    name: Mapped[str_255] = mapped_column()

    # Relationships
    meta: Mapped[Meta] = relationship()
    customer: Mapped[Customer] = relationship(back_populates="groups")
    children: Mapped[Dict[str_26, "Group"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="parent",
        collection_class=attribute_keyed_dict("id"),
    )
    group_permission: Mapped[list["GroupPermission"]] = relationship(
        back_populates="group"
    )
    parent: Mapped[Optional["Group"]] = relationship(
        back_populates="children",
        remote_side=[id],
    )
    filters: Mapped[list["Filter"]] = relationship(back_populates="group")
    queries: Mapped[list["Query"]] = relationship(back_populates="group")

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
    customer_name: AssociationProxy[str_255] = association_proxy(
        target_collection="customer", attr="name"
    )

    def __str__(self) -> str:
        return f"{self.customer_name} - {self.name}"


class GroupPermission(Base):
    __tablename__ = "group_permission"
    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_group_permission_name"),
        UniqueConstraint(
            "group_id", "permissions", name="uq_group_permission_permissions"
        ),
        {
            "schema": "auth",
            "comment": """
                Permissions assigned to a group.
                Created automatically by the DB via a trigger when a new group is created.
                group_permission records are created for each group with the following combinations of permissions:
                    [READ]
                    [READ, CREATE]
                    [READ, CREATE, UPDATE]
                    [READ, CREATE, DELETE]
                    [READ, CREATE, UPDATE, DELETE]
                    [READ, UPDATE]
                    [READ, UPDATE, DELETE]
                    [READ, DELETE]
                Deleted automatically by the DB via the FK Constraints ondelete when an group is deleted.
            """,
            "info": {"vertex": True},
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
    group_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.group.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "PROVIDES_PERMISSIONS_FOR_ACCESSING_DATA_OF_GROUP"},
    )
    name: Mapped[str_255] = mapped_column()
    permissions: Mapped[list] = mapped_column(
        ARRAY(ENUM(Permission, name="permission", create_type=True, schema="auth")),
    )

    # Relationships
    group: Mapped[Group] = relationship(back_populates="group_permission")

    # AssociationProxies
    group_name: AssociationProxy[str_255] = association_proxy(
        target_collection="group", attr="name"
    )

    def __str__(self) -> str:
        return f"{self.group_name} - {self.name} - {self.permissions}"


class Role(Base):
    __tablename__ = "role"
    __table_args__ = (
        Index("ix_customer_id_name", "customer_id", "name"),
        {
            "schema": "auth",
            "comment": """
                Roles, created by end user group admins, enable assignment of group_permissions
                by functionality, department, etc... to users.
            """,
            "info": {"vertex": True, "audited": True},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=func.audit.insert_meta_record(),
        server_onupdate=FetchedValue(),
        info={"edge": False},
    )
    customer_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.customer.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "LIMITS_ACCESS_TO_DATA_OF_CUSTOMER"},
    )
    name: Mapped[str_255] = mapped_column()
    description: Mapped[str] = mapped_column()

    # Relationships
    meta: Mapped[Meta] = relationship()
    customer: Mapped[Customer] = relationship(back_populates="roles")
    users: Mapped[list[User]] = relationship(
        secondary="auth.user__role", back_populates="roles"
    )

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
    customer_name: AssociationProxy[str_255] = association_proxy(
        target_collection="customer", attr="name"
    )


role_group_permission = Table(
    "role__group_permission",
    Base.metadata,
    Column(
        "role_id",
        VARCHAR(26),
        ForeignKey("auth.role.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        info={"start_vertex": True},
    ),
    Column(
        "group_permission_id",
        VARCHAR(26),
        ForeignKey("auth.group_permission.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        info={"end_vertex": True},
    ),
    Index(
        "ix_role_id__group_permission_id",
        "role_id",
        "group_permission_id",
    ),
    comment="Assigned by customer_admin users to assign group_permissions to roles based on organization requirements.",
    schema="auth",
    info={"edge": "HAS_GROUP_PERMISSION", "audited": True},
)


user_role = Table(
    "user__role",
    Base.metadata,
    Column(
        "user_id",
        VARCHAR(26),
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        info={"start_vertex": True},
    ),
    Column(
        "role_id",
        VARCHAR(26),
        ForeignKey("auth.role.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        info={"end_vertex": True},
    ),
    Index(
        "ix_user_id__role_id",
        "user_id",
        "role_id",
    ),
    comment="Assigned by customer_admin users to assign roles to users based on organization requirements.",
    schema="auth",
    info={"edge": "HAS_ROLE", "audited": True},
)
