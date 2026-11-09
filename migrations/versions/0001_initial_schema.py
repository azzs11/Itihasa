"""Initial schema: five core tables and pgvector extension.

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector must exist before any vector column is added in a later migration.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc_id", sa.String, nullable=False),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("doc_type", sa.String, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("language", sa.String, nullable=True),
        sa.Column("script", sa.String, nullable=True),
        sa.Column("licence", sa.String, nullable=False),
        sa.Column("can_redistribute", sa.Boolean, nullable=False),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("entities", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("places", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("period", postgresql.JSONB, nullable=True),
        sa.Column("creators", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("date", sa.String, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_version_id", sa.Integer, nullable=True),
    )
    op.create_index("ix_records_doc_id", "records", ["doc_id"], unique=True)
    op.create_index("ix_records_source", "records", ["source"])
    op.create_index("ix_records_doc_type", "records", ["doc_type"])
    op.create_index("ix_records_language", "records", ["language"])

    op.create_table(
        "record_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "record_id",
            sa.Integer,
            sa.ForeignKey("records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("record_id", "version_number", name="uq_record_version"),
    )
    op.create_index("ix_record_versions_record_id", "record_versions", ["record_id"])

    op.create_table(
        "provenance_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "record_id",
            sa.Integer,
            sa.ForeignKey("records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Integer,
            sa.ForeignKey("record_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("event_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_detail", sa.Text, nullable=True),
        sa.Column("agent", sa.String, nullable=False),
        sa.Column("tool_name", sa.String, nullable=False),
        sa.Column("tool_version", sa.String, nullable=False),
        sa.Column("model_name", sa.String, nullable=False, server_default=""),
        sa.Column("model_version", sa.String, nullable=False, server_default=""),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("outcome", sa.String, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
    )
    op.create_index("ix_provenance_events_record_id", "provenance_events", ["record_id"])
    op.create_index("ix_provenance_events_event_type", "provenance_events", ["event_type"])
    op.create_index("ix_provenance_events_event_datetime", "provenance_events", ["event_datetime"])

    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("node_type", sa.String, nullable=False),
        sa.Column("wikidata_qid", sa.String, nullable=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("properties", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_nodes_node_type", "graph_nodes", ["node_type"])
    op.create_index("ix_graph_nodes_wikidata_qid", "graph_nodes", ["wikidata_qid"], unique=True)

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "source_node_id",
            sa.Integer,
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            sa.Integer,
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String, nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_node_id", "target_node_id", "relation_type", name="uq_graph_edge"
        ),
    )
    op.create_index("ix_graph_edges_source_node_id", "graph_edges", ["source_node_id"])
    op.create_index("ix_graph_edges_relation_type", "graph_edges", ["relation_type"])


def downgrade() -> None:
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("provenance_events")
    op.drop_table("record_versions")
    op.drop_table("records")
    # Leave the vector extension in place; removing it could affect other databases
    # on the same server.
