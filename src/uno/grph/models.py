from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import (
    VARCHAR,
)
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy import (
    ForeignKey,
    FetchedValue,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uno.base import Base, str_26, str_255
from uno.audit.models import Meta
from uno.auth.models import Customer


class EdgeType(Base):
    __tablename__ = "edge_type"

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=func.audit.insert_meta_record(),
        server_onupdate=FetchedValue(),
        index=True,
    )
    customer_id: Mapped[str_26] = mapped_column(
        ForeignKey("auth.customer.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str_26] = mapped_column(VARCHAR(26), nullable=False)
    description: Mapped[str_255] = mapped_column(VARCHAR(255))

    # Relationships
    meta: Mapped[Meta] = relationship(primaryjoin=id == Meta.id, backref="edge_types")
    edges: Mapped["Edge"] = relationship("Edge", backref="edge_type")
    customer: Mapped[Customer] = relationship(
        primaryjoin=customer_id == Customer.id, backref="edge_types"
    )


class Edge(Base):
    __tablename__ = "edge"
    __table_args__ = (
        UniqueConstraint("start_id", "end_id", "edge_type"),
        CheckConstraint("start_id != end_id"),
        Index("edge_start_end_type_idx", "start_id", "end_id", "edge_type"),
    )

    # Columns
    start_id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
    )
    end_id: Mapped[str_26] = mapped_column(
        ForeignKey("audit.meta.id", ondelete="CASCADE"),
        primary_key=True,
    )
    edge_type: Mapped[str_26] = mapped_column(
        ForeignKey("grph.edge_type.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships

    start: Mapped[Meta] = relationship(
        primaryjoin=start_id == Meta.id, backref="start_edges"
    )

    end: Mapped[Meta] = relationship(primaryjoin=end_id == Meta.id, backref="end_edges")
