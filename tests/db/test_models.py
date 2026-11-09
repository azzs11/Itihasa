"""Smoke tests for ORM models and the initial migration.

These tests verify that the migration created the expected tables and that
basic insert/rollback works for each model.  They require a live PostgreSQL
database and are marked ``db`` accordingly.
"""

from datetime import UTC, datetime

import pytest

from itihasa.db.models import (
    GraphEdgeORM,
    GraphNodeORM,
    ProvenanceEventORM,
    RecordORM,
    RecordVersionORM,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _record(doc_id: str = "wikidata:Q11739") -> RecordORM:
    return RecordORM(
        doc_id=doc_id,
        source="wikidata",
        source_url="https://www.wikidata.org/wiki/Q11739",
        doc_type="archival_record",
        title="Taj Mahal",
        licence="CC-BY-4.0",
        can_redistribute=True,
        fetched_at=_now(),
        checksum="a" * 64,
        created_at=_now(),
        updated_at=_now(),
    )


@pytest.mark.db
def test_record_insert_and_rollback(db_session) -> None:
    db_session.add(_record())
    db_session.flush()
    count = db_session.query(RecordORM).count()
    assert count == 1
    # Transaction rolls back after the test; next test sees an empty table.


@pytest.mark.db
def test_record_version_linked_to_record(db_session) -> None:
    rec = _record("wikidata:Q11740")
    db_session.add(rec)
    db_session.flush()

    ver = RecordVersionORM(
        record_id=rec.id,
        version_number=1,
        snapshot={"title": "Taj Mahal"},
        created_at=_now(),
    )
    db_session.add(ver)
    db_session.flush()
    assert ver.id is not None


@pytest.mark.db
def test_provenance_event_linked_to_record(db_session) -> None:
    rec = _record("wikidata:Q11741")
    db_session.add(rec)
    db_session.flush()

    event = ProvenanceEventORM(
        record_id=rec.id,
        event_type="fetch",
        event_datetime=_now(),
        agent="itihasa.collect.wikidata",
        tool_name="SPARQLWrapper",
        tool_version="2.0.0",
        outcome="success",
    )
    db_session.add(event)
    db_session.flush()
    assert event.id is not None


@pytest.mark.db
def test_graph_node_and_edge(db_session) -> None:
    n1 = GraphNodeORM(node_type="site", label="Taj Mahal", created_at=_now())
    n2 = GraphNodeORM(node_type="dynasty", label="Mughal", created_at=_now())
    db_session.add_all([n1, n2])
    db_session.flush()

    edge = GraphEdgeORM(
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="associated_with",
        created_at=_now(),
    )
    db_session.add(edge)
    db_session.flush()
    assert edge.id is not None
