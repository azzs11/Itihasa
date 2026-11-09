"""Tests for the Record model and all custom field validators."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from itihasa.schema.record import DocType, Period, PlaceRef, Record


def _valid_record(**overrides: object) -> dict[str, object]:
    """Return a minimal valid Record payload, with optional field overrides."""
    base: dict[str, object] = {
        "doc_id": "wikidata:Q11739",
        "source": "wikidata",
        "source_url": "https://www.wikidata.org/wiki/Q11739",
        "doc_type": DocType.ARCHIVAL_RECORD,
        "licence": "CC-BY-4.0",
        "can_redistribute": True,
        "language": "hi",
        "script": "Deva",
        "title": "Taj Mahal",
        "fetched_at": datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC),
        "checksum": "a" * 64,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


def test_valid_record_round_trips() -> None:
    r = Record(**_valid_record())
    assert r.doc_id == "wikidata:Q11739"
    assert r.language == "hi"


def test_entities_and_places_default_empty() -> None:
    r = Record(**_valid_record())
    assert r.entities == []
    assert r.places == []


def test_place_ref_accepted() -> None:
    r = Record(
        **_valid_record(
            places=[PlaceRef(qid="Q11739", label="Taj Mahal", latitude=27.17, longitude=78.04)]
        )
    )
    assert r.places[0].qid == "Q11739"


def test_period_accepted() -> None:
    r = Record(**_valid_record(period=Period(edtf_start="1631", edtf_end="1653")))
    assert r.period is not None
    assert r.period.edtf_start == "1631"


def test_cc_uri_licence_accepted() -> None:
    r = Record(**_valid_record(licence="https://creativecommons.org/licenses/by/4.0/"))
    assert r.licence.startswith("https://creativecommons.org/")


def test_unknown_licence_accepted() -> None:
    r = Record(**_valid_record(licence="UNKNOWN"))
    assert r.licence == "UNKNOWN"


# ---------------------------------------------------------------------------
# EDTFDate
# ---------------------------------------------------------------------------


def test_empty_edtf_rejected() -> None:
    with pytest.raises(ValidationError, match="EDTF"):
        Record(**_valid_record(date=""))


def test_whitespace_edtf_rejected() -> None:
    with pytest.raises(ValidationError, match="EDTF"):
        Record(**_valid_record(date="   "))


# ---------------------------------------------------------------------------
# BCP 47
# ---------------------------------------------------------------------------


def test_valid_bcp47_normalised_to_lowercase() -> None:
    r = Record(**_valid_record(language="HI"))
    assert r.language == "hi"


def test_invalid_bcp47_rejected() -> None:
    with pytest.raises(ValidationError, match="BCP 47"):
        Record(**_valid_record(language="not valid tag!"))


# ---------------------------------------------------------------------------
# ISO 15924
# ---------------------------------------------------------------------------


def test_invalid_script_rejected() -> None:
    with pytest.raises(ValidationError, match="ISO 15924"):
        Record(**_valid_record(script="deva"))  # must be title-case


def test_valid_script_accepted() -> None:
    r = Record(**_valid_record(script="Gran"))
    assert r.script == "Gran"


# ---------------------------------------------------------------------------
# SPDX / licence
# ---------------------------------------------------------------------------


def test_invalid_licence_rejected() -> None:
    with pytest.raises(ValidationError, match="SPDX"):
        Record(**_valid_record(licence="not a licence !!!"))


# ---------------------------------------------------------------------------
# WikidataQID
# ---------------------------------------------------------------------------


def test_invalid_qid_in_entities_rejected() -> None:
    with pytest.raises(ValidationError, match="Wikidata QID"):
        Record(**_valid_record(entities=["Q11739", "not-a-qid"]))


def test_itihasa_local_id_accepted() -> None:
    r = Record(**_valid_record(entities=["I1001"]))
    assert r.entities == ["I1001"]


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


def test_short_checksum_rejected() -> None:
    with pytest.raises(ValidationError):
        Record(**_valid_record(checksum="abc123"))


def test_non_hex_checksum_rejected() -> None:
    with pytest.raises(ValidationError):
        Record(**_valid_record(checksum="z" * 64))


# ---------------------------------------------------------------------------
# Extra fields
# ---------------------------------------------------------------------------


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Record(**_valid_record(unknown_field="oops"))
