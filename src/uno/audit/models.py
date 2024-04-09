import datetime
from typing import Optional

from sqlalchemy.sql import func, text
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.dialects.postgresql import (
    ENUM,
)
from sqlalchemy import (
    ForeignKey,
    Identity,
    FetchedValue,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uno.enumerations import (
    AccessLogAction,
    AccessLogSeverity,
)
from uno.base import Base, str_26, str_128, str_255


class Meta(Base):
    __tablename__ = "meta"
    __table_args__ = {"schema": "audit", "comment": "Record metadata"}

    # Columns
    id: Mapped[str_26] = mapped_column(
        primary_key=True,
        server_default=func.audit.generate_ulid(),
    )
    is_active: Mapped[bool] = mapped_column(
        server_default=text("true"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        server_default=text("false"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.current_timestamp(),
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.current_timestamp(),
        server_onupdate=FetchedValue(),
    )


class AccessLog(Base):
    __tablename__ = "access_log"
    __table_args__ = {"schema": "audit", "comment": "Application end-user access log"}

    # Columns
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    user_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        index=True,
    )
    action_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(),
    )
    action: Mapped[AccessLogAction] = mapped_column(
        ENUM(AccessLogAction, name="accesslogaction", create_type=True, schema="audit"),
        default=AccessLogAction.TOKEN_RENEWED,
    )
    message: Mapped[str_255]
    severity: Mapped[AccessLogSeverity] = mapped_column(
        ENUM(
            AccessLogAction, name="accesslogseverity", create_type=True, schema="audit"
        ),
        default=AccessLogSeverity.INFO,
    )
    client_hint_hash: Mapped[Optional[str_128]]
    token: Mapped[Optional[str_128]]
    token_renewal_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="access_logs")

    # AssociationProxies
    email: AssociationProxy[str_255] = association_proxy(
        target_collection="user", attr="email"
    )
    handle: AssociationProxy[str_255] = association_proxy(
        target_collection="user", attr="handle"
    )
