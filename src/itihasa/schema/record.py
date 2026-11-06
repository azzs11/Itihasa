"""Common record schema that every source connector maps into."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from itihasa.schema.fields import (
    BCP47Tag,
    ConfidenceFloat,
    EDTFDate,
    Iso15924Script,
    SpdxLicence,
    WikidataQID,
)


class DocType(StrEnum):
    ARTICLE = "article"
    BOOK = "book"
    REPORT = "report"
    MANUSCRIPT = "manuscript"
    ARCHIVAL_RECORD = "archival_record"
    THESIS = "thesis"
    PAPER = "paper"
    OBJECT_RECORD = "object_record"
    IMAGE = "image"


class PlaceRef(BaseModel):
    """A place with its Wikidata QID and optional coordinates."""

    model_config = ConfigDict(frozen=True)

    qid: WikidataQID
    label: str = ""
    latitude: float | None = None
    longitude: float | None = None


class Period(BaseModel):
    """A historical period expressed as an EDTF interval plus the original string."""

    model_config = ConfigDict(frozen=True)

    edtf_start: EDTFDate | None = None
    edtf_end: EDTFDate | None = None
    # Original string from the source, kept for provenance.
    original: str = ""


class FieldConfidence(BaseModel):
    """Confidence metadata attached to a single machine-produced field value."""

    model_config = ConfigDict(frozen=True)

    value: ConfidenceFloat
    tool: str
    tool_version: str
    model_name: str = ""
    model_version: str = ""


class Record(BaseModel):
    """A normalised document record in the common schema.

    Every source connector maps its raw response into this model.
    Fields produced by machine (entities, places, period, language, script,
    summary) carry a corresponding entry in `field_confidence`.
    Raw source metadata is preserved losslessly in `raw_metadata`.
    """

    model_config = ConfigDict(
        frozen=True,
        # Reject unexpected fields rather than silently ignoring them.
        extra="forbid",
        # Allow populating by field name or alias.
        populate_by_name=True,
    )

    # --- Identity ---
    doc_id: str = Field(description="Stable identifier, e.g. 'wikidata:Q12345'")
    source: str = Field(description="Short source name, e.g. 'wikidata', 'wikipedia'")
    source_url: str = Field(description="Canonical URL of the source record")

    # --- Content type ---
    doc_type: DocType

    # --- Rights ---
    licence: SpdxLicence
    can_redistribute: bool = Field(
        description="True when the licence permits redistribution of the full text"
    )

    # --- Language and script ---
    language: BCP47Tag | None = None
    script: Iso15924Script | None = None

    # --- Content ---
    title: str
    text: str | None = Field(
        default=None,
        description="Full text if available; None for metadata-only records",
    )
    summary: str | None = None

    # --- Entities and places ---
    entities: list[WikidataQID] = Field(default_factory=list)
    places: list[PlaceRef] = Field(default_factory=list)

    # --- Temporal ---
    period: Period | None = None

    # --- Creators and date ---
    creators: list[str] = Field(default_factory=list)
    date: EDTFDate | None = None

    # --- Provenance ---
    fetched_at: datetime
    checksum: str = Field(
        description="SHA-256 hex digest of the raw source response",
        pattern=r"^[0-9a-f]{64}$",
    )

    # --- Machine-field confidence ---
    field_confidence: dict[str, FieldConfidence] = Field(
        default_factory=dict,
        description="Maps field name to its confidence metadata for machine-produced fields",
    )

    # --- Raw source preservation ---
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Full source API or SPARQL response before any normalisation",
    )
