"""Custom annotated types for the common record schema.

Each type wraps a Python primitive and validates format at ingest time,
so malformed values are caught at the boundary rather than stored silently.
"""

import re
from typing import Annotated

from pydantic import AfterValidator


def _validate_edtf(v: str) -> str:
    """Reject strings that cannot be a minimal EDTF Level 0/1 date or interval.

    Full EDTF compliance is not enforced here; the validator blocks obviously
    wrong values (empty string, bare whitespace) and passes everything else
    to the normaliser in src/itihasa/normalise/dates.py.
    """
    if not v or not v.strip():
        raise ValueError("EDTF date must not be empty")
    return v


def _validate_bcp47(v: str) -> str:
    """Accept well-formed BCP 47 primary language tags (e.g. 'hi', 'sa', 'ta').

    Only primary subtag and optional script/region subtags are validated here.
    Full IANA registry lookup is out of scope for ingest-time validation.
    """
    # BCP 47 subtags are ASCII letters and digits separated by hyphens.
    if not re.fullmatch(r"[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*", v):
        raise ValueError(f"Not a valid BCP 47 language tag: {v!r}")
    return v.lower()


def _validate_iso15924(v: str) -> str:
    """Accept ISO 15924 four-letter script codes (e.g. 'Deva', 'Gran', 'Taml')."""
    if not re.fullmatch(r"[A-Z][a-z]{3}", v):
        raise ValueError(f"Not a valid ISO 15924 script code: {v!r}")
    return v


def _validate_spdx(v: str) -> str:
    """Accept SPDX licence identifiers or Creative Commons URIs.

    SPDX identifiers use alphanumerics, hyphens and dots (e.g. 'Apache-2.0',
    'CC-BY-4.0'). Creative Commons URIs begin with 'https://creativecommons.org/'.
    'UNLICENSED' and 'UNKNOWN' are also permitted as sentinel values.
    """
    if v in {"UNLICENSED", "UNKNOWN"}:
        return v
    if v.startswith("https://creativecommons.org/"):
        return v
    if re.fullmatch(r"[A-Za-z0-9\-\.+]+([ ]+[Oo][Rr][ ]+[A-Za-z0-9\-\.+]+)*", v):
        return v
    raise ValueError(f"Not a recognised SPDX identifier or CC URI: {v!r}")


def _validate_qid(v: str) -> str:
    """Accept Wikidata QIDs ('Q' followed by digits) or Itihasa local IDs ('I' prefix)."""
    if not re.fullmatch(r"[QI]\d+", v):
        raise ValueError(f"Not a valid Wikidata QID or Itihasa ID: {v!r}")
    return v


def _validate_confidence(v: float) -> float:
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"Confidence must be in [0.0, 1.0], got {v}")
    return v


# Exported annotated types used in record.py and provenance models.
EDTFDate = Annotated[str, AfterValidator(_validate_edtf)]
BCP47Tag = Annotated[str, AfterValidator(_validate_bcp47)]
Iso15924Script = Annotated[str, AfterValidator(_validate_iso15924)]
SpdxLicence = Annotated[str, AfterValidator(_validate_spdx)]
WikidataQID = Annotated[str, AfterValidator(_validate_qid)]
ConfidenceFloat = Annotated[float, AfterValidator(_validate_confidence)]
