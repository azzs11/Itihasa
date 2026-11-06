"""SQLAlchemy ORM models for the five core tables.

All models use the SQLAlchemy 2.0 declarative style (Mapped[], mapped_column()).
record_embeddings is deferred until the embedding-model decision record is filed.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RecordORM(Base):
    """Current state of a collected document record."""

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    script: Mapped[str | None] = mapped_column(String, nullable=True)
    licence: Mapped[str] = mapped_column(String, nullable=False)
    can_redistribute: Mapped[bool] = mapped_column(Boolean, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured fields stored as JSONB for flexible querying.
    entities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    places: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    period: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    creators: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    date: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    # Full source API or SPARQL response before any normalisation.
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    versions: Mapped[list["RecordVersionORM"]] = relationship(
        "RecordVersionORM", back_populates="record", cascade="all, delete-orphan"
    )
    provenance_events: Mapped[list["ProvenanceEventORM"]] = relationship(
        "ProvenanceEventORM", back_populates="record", cascade="all, delete-orphan"
    )


class RecordVersionORM(Base):
    """Immutable snapshot of a record at a point in time.

    One row is inserted per change; rows are never updated.
    """

    __tablename__ = "record_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full record state at this version, stored as JSONB.
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    record: Mapped["RecordORM"] = relationship("RecordORM", back_populates="versions")
    provenance_events: Mapped[list["ProvenanceEventORM"]] = relationship(
        "ProvenanceEventORM", back_populates="version"
    )

    __table_args__ = (
        UniqueConstraint("record_id", "version_number", name="uq_record_version"),
    )


class ProvenanceEventORM(Base):
    """PREMIS-style provenance event linked to a record and version.

    One row per machine operation (fetch, OCR, entity-link, dedup, etc.).
    """

    __tablename__ = "provenance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("record_versions.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    event_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent: Mapped[str] = mapped_column(String, nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_version: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    model_version: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    record: Mapped["RecordORM"] = relationship(
        "RecordORM", back_populates="provenance_events"
    )
    version: Mapped["RecordVersionORM | None"] = relationship(
        "RecordVersionORM", back_populates="provenance_events"
    )


class GraphNodeORM(Base):
    """A node in the knowledge graph."""

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    wikidata_qid: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True, index=True
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    outgoing_edges: Mapped[list["GraphEdgeORM"]] = relationship(
        "GraphEdgeORM",
        foreign_keys="GraphEdgeORM.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["GraphEdgeORM"]] = relationship(
        "GraphEdgeORM",
        foreign_keys="GraphEdgeORM.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class GraphEdgeORM(Base):
    """A directed edge in the knowledge graph."""

    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_node: Mapped["GraphNodeORM"] = relationship(
        "GraphNodeORM", foreign_keys=[source_node_id], back_populates="outgoing_edges"
    )
    target_node: Mapped["GraphNodeORM"] = relationship(
        "GraphNodeORM", foreign_keys=[target_node_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        UniqueConstraint(
            "source_node_id", "target_node_id", "relation_type", name="uq_graph_edge"
        ),
    )
