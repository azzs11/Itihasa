"""Count-only probes for all Start-stage sources.

Runs one lightweight query per source, prints the count, and saves a JSON
record under results/probes/<YYYY-MM-DD>/ with the date, source, query, and
count.  No data is downloaded; no cleaning is done.

Usage:
    uv run python scripts/probe_counts.py

Requires:
    ITIHASA_CONTACT_EMAIL in .env (used in User-Agent headers).
    ZENODO_API_KEY in .env (optional; raises rate limit from 30 to 60 req/min
    for search endpoints and allows 100 results per page instead of 25).

Sources probed:
    wikidata   - SPARQL COUNT of Karnataka heritage items (P131* = Q1185)
    wikidata_coords - extra items caught by bounding-box when P131 is absent
    wikipedia_en - category member count via MediaWiki API
    wikipedia_kn - category member count via MediaWiki API
    commons    - category member count via MediaWiki API
    internet_archive - numFound from IA advanced search
    siddham    - hits.total from Zenodo community=siddham search
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONTACT_EMAIL = os.environ.get("ITIHASA_CONTACT_EMAIL", "")
if not CONTACT_EMAIL:
    sys.exit("ITIHASA_CONTACT_EMAIL is not set. Add it to .env before running probes.")

USER_AGENT = f"Itihasa/0.1 (+https://github.com/Akchhya1108/Itihasa; {CONTACT_EMAIL})"
ZENODO_API_KEY = os.environ.get("ZENODO_API_KEY", "")

RESULTS_DIR = Path("results") / "probes" / date.today().isoformat()
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Karnataka Wikidata QID
KARNATAKA_QID = "Q1185"

# Bounding box for Karnataka (approximate): lat 11.5–18.5, lon 74.0–78.6
KARNATAKA_BBOX = {"south": 11.5, "north": 18.5, "west": 74.0, "east": 78.6}

# Heritage-relevant instance types (P31) for coordinate probe.
# All QIDs verified against Wikidata labels; see docs/decisions/ for rationale.
# Q9259 (World Heritage Site) is handled via P1435 in the full connector,
# not via P31, so it is excluded here.
HERITAGE_INSTANCES = [
    "Q839954",  # archaeological site
    "Q16970",  # church building
    "Q44539",  # temple
    "Q842402",  # Hindu temple
    "Q2613100",  # Jain temple
    "Q33506",  # museum
    "Q1785071",  # fort
    "Q4989906",  # monument
    "Q1640824",  # inscription
    "Q87167",  # manuscript
    "Q1081138",  # historic site
    "Q16560",  # palace
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _save(source: str, query: str | dict, count: int | str, notes: str = "") -> None:
    record = {
        "source": source,
        "probed_at": datetime.now(UTC).isoformat(),
        "query": query,
        "count": count,
        "notes": notes,
    }
    out = RESULTS_DIR / f"{source}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    label = f"{count:,}" if isinstance(count, int) else count
    print(f"  {source:<30} {label}")


def _save_error(source: str, error: str) -> None:
    record = {
        "source": source,
        "probed_at": datetime.now(UTC).isoformat(),
        "count": "ERROR",
        "error": error,
    }
    out = RESULTS_DIR / f"{source}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {source:<30} ERROR: {error}")


def _get(
    session: requests.Session, url: str, params: dict | None = None, headers: dict | None = None
) -> requests.Response:
    r = session.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    time.sleep(1)  # polite pause between requests
    return r


# ---------------------------------------------------------------------------
# Wikidata SPARQL
# ---------------------------------------------------------------------------

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Direct P131 (no transitive path) and direct P31 keep the query well under the
# SPARQL endpoint's 60-second wall-clock limit.  Counts are lower bounds: items
# linked only via intermediate districts/taluks and items whose type is a
# subclass (not direct instance) of the listed types are not counted here.
# The full connector will use a wider query with SPARQL 1.1 property paths.
WIKIDATA_COUNT_SPARQL = f"""
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {{
  ?item wdt:P131 wd:{KARNATAKA_QID} .
  ?item wdt:P31 ?type .
  VALUES ?type {{
    wd:Q839954   # archaeological site
    wd:Q16970    # church building
    wd:Q44539    # temple
    wd:Q842402   # Hindu temple
    wd:Q2613100  # Jain temple
    wd:Q33506    # museum
    wd:Q1785071  # fort
    wd:Q4989906  # monument
    wd:Q1640824  # inscription
    wd:Q87167    # manuscript
    wd:Q1081138  # historic site
    wd:Q16560    # palace
  }}
}}
""".strip()

# wikibase:around is an indexed service (unlike geof: FILTER which scans all
# coordinate items).  Center 15.3°N 75.7°E, radius 350 km covers Karnataka
# with some overspill into neighbouring states; that is acceptable for a probe.
# FILTER NOT EXISTS { ?item wdt:P131 [] } excludes items already counted above.
KARNATAKA_CENTER_LON = 75.7
KARNATAKA_CENTER_LAT = 15.3
KARNATAKA_RADIUS_KM = 350

WIKIDATA_COORDS_SPARQL = f"""
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?coords .
    bd:serviceParam wikibase:center "Point({KARNATAKA_CENTER_LON} {KARNATAKA_CENTER_LAT})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "{KARNATAKA_RADIUS_KM}" .
  }}
  ?item wdt:P31 ?type .
  VALUES ?type {{
    wd:Q839954 wd:Q16970 wd:Q44539 wd:Q842402 wd:Q2613100
    wd:Q33506 wd:Q1785071 wd:Q4989906 wd:Q1640824 wd:Q87167
    wd:Q1081138 wd:Q16560
  }}
  FILTER NOT EXISTS {{ ?item wdt:P131 [] }}
}}
""".strip()


def probe_wikidata(session: requests.Session) -> None:
    print("\nWikidata")
    for label, sparql in [
        ("wikidata", WIKIDATA_COUNT_SPARQL),
        ("wikidata_coords", WIKIDATA_COORDS_SPARQL),
    ]:
        try:
            r = _get(
                session,
                SPARQL_ENDPOINT,
                params={"query": sparql, "format": "json"},
                headers={"Accept": "application/sparql-results+json"},
            )
            count = int(r.json()["results"]["bindings"][0]["count"]["value"])
            _save(label, sparql, count)
        except Exception as exc:
            _save_error(label, str(exc))


# ---------------------------------------------------------------------------
# MediaWiki (Wikipedia EN, Wikipedia KN, Commons)
# ---------------------------------------------------------------------------

MEDIAWIKI_EN = "https://en.wikipedia.org/w/api.php"
MEDIAWIKI_KN = "https://kn.wikipedia.org/w/api.php"
MEDIAWIKI_COMMONS = "https://commons.wikimedia.org/w/api.php"

# Seed categories per wiki.  Depth is handled in the full connector; here we
# just count direct members of each seed category for a lower-bound estimate.
WP_EN_SEEDS = [
    "Heritage sites in Karnataka",
    "Temples in Karnataka",
    "Monuments and memorials in Karnataka",
    "Inscriptions in Karnataka",
    "History of Karnataka",
    "Kannada literature",
    "Manuscripts in Karnataka",
]

WP_KN_SEEDS = [
    "ಕರ್ನಾಟಕದ ಪರಂಪರೆ ತಾಣಗಳು",  # Heritage sites in Karnataka
    "ಕರ್ನಾಟಕದ ದೇವಾಲಯಗಳು",  # Temples in Karnataka
    "ಕರ್ನಾಟಕದ ಇತಿಹಾಸ",  # History of Karnataka
    "ಕನ್ನಡ ಸಾಹಿತ್ಯ",  # Kannada literature
]

COMMONS_SEEDS = [
    "Heritage sites in Karnataka",
    "Temples in Karnataka",
    "Inscriptions in Karnataka",
    "Archaeological sites in Karnataka",
    "Monuments and memorials in Karnataka",
]


def _mw_category_size(session: requests.Session, api: str, category: str) -> int:
    """Return the categoryinfo size for one category (pages + files + subcats)."""
    r = _get(
        session,
        api,
        params={
            "action": "query",
            "titles": f"Category:{category}",
            "prop": "categoryinfo",
            "format": "json",
        },
    )
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        ci = page.get("categoryinfo", {})
        return ci.get("size", 0)
    return 0


def _probe_mediawiki(session: requests.Session, source: str, api: str, seeds: list[str]) -> None:
    total = 0
    per_cat: dict[str, int] = {}
    for cat in seeds:
        n = _mw_category_size(session, api, cat)
        per_cat[cat] = n
        total += n
    _save(
        source,
        {"api": api, "seed_categories": seeds, "per_category": per_cat},
        total,
        notes="Sum of direct category members across seed categories; "
        "subcategories not yet traversed.",
    )


def probe_mediawiki(session: requests.Session) -> None:
    print("\nWikipedia EN / KN / Commons")
    for source, api, seeds in [
        ("wikipedia_en", MEDIAWIKI_EN, WP_EN_SEEDS),
        ("wikipedia_kn", MEDIAWIKI_KN, WP_KN_SEEDS),
        ("commons", MEDIAWIKI_COMMONS, COMMONS_SEEDS),
    ]:
        try:
            _probe_mediawiki(session, source, api, seeds)
        except Exception as exc:
            _save_error(source, str(exc))


# ---------------------------------------------------------------------------
# Internet Archive
# ---------------------------------------------------------------------------

IA_SEARCH = "https://archive.org/advancedsearch.php"

IA_QUERIES = {
    "texts": (
        "(language:(Kannada) OR language:(kan) OR subject:(Karnataka)) AND mediatype:(texts)"
    ),
    "images": ("(language:(Kannada) OR subject:(Karnataka heritage)) AND mediatype:(image)"),
}


def probe_internet_archive(session: requests.Session) -> None:
    print("\nInternet Archive")
    try:
        total = 0
        per_query: dict[str, int] = {}
        for label, q in IA_QUERIES.items():
            r = _get(
                session,
                IA_SEARCH,
                params={
                    "q": q,
                    "rows": 0,
                    "output": "json",
                },
            )
            n = r.json()["response"]["numFound"]
            per_query[label] = n
            total += n
        _save(
            "internet_archive",
            {"queries": IA_QUERIES},
            total,
            notes="numFound from IA Lucene search; texts + images combined. "
            "Will be narrowed by heritage subject filter in connector.",
        )
    except Exception as exc:
        _save_error("internet_archive", str(exc))


# ---------------------------------------------------------------------------
# SIDDHAM via Zenodo
# ---------------------------------------------------------------------------

ZENODO_SEARCH = "https://zenodo.org/api/records"

# Community slug confirmed: https://zenodo.org/communities/siddham/
# Two additional sub-communities exist (siddhamdata, siddhamassets) but
# siddham is the umbrella containing all inscription records.
SIDDHAM_COMMUNITY = "siddham"


def probe_siddham(session: requests.Session) -> None:
    print("\nSIDDHAM (Zenodo)")
    try:
        headers: dict[str, str] = {}
        if ZENODO_API_KEY:
            headers["Authorization"] = f"Bearer {ZENODO_API_KEY}"

        r_all = _get(
            session,
            ZENODO_SEARCH,
            params={
                "communities": SIDDHAM_COMMUNITY,
                "size": 1,
                "page": 1,
            },
            headers=headers,
        )
        total_all = r_all.json()["hits"]["total"]

        r_kn = _get(
            session,
            ZENODO_SEARCH,
            params={
                "communities": SIDDHAM_COMMUNITY,
                "q": "Karnataka",
                "size": 1,
                "page": 1,
            },
            headers=headers,
        )
        total_karnataka = r_kn.json()["hits"]["total"]

        _save(
            "siddham",
            {
                "endpoint": ZENODO_SEARCH,
                "community": SIDDHAM_COMMUNITY,
                "karnataka_query": "q=Karnataka",
            },
            total_all,
            notes=(
                f"Total records in siddham community: {total_all}. "
                f"Records matching q=Karnataka (keyword/title): {total_karnataka}. "
                "Karnataka count is a lower bound; attached metadata JSON files "
                "may contain place data not indexed as Zenodo keywords."
            ),
        )
        print(f"    siddham total={total_all:,}, Karnataka keyword match={total_karnataka:,}")
    except Exception as exc:
        _save_error("siddham", str(exc))


# ---------------------------------------------------------------------------
# Pandit
# ---------------------------------------------------------------------------

# Pandit exposes a CSV export endpoint, not a REST count API.
# The 2024-12-23 export used in Pāṇḍityatāraka (WSC 2025) contained 67,529
# entities. The download URL is:
#   https://panditproject.org/search/pandit-entities-export?page&_format=csv
# A count of Karnataka-relevant records requires downloading and filtering the
# CSV. This probe fetches only the HTTP headers to confirm the endpoint is
# reachable and records the known total from the published export.

PANDIT_EXPORT_URL = "https://panditproject.org/search/pandit-entities-export?page&_format=csv"
PANDIT_TOTAL_FROM_PAPER = 67529  # Pāṇḍityatāraka, WSC 2025, export dated 2024-12-23


def probe_pandit(session: requests.Session) -> None:
    print("\nPandit")
    try:
        r = session.head(PANDIT_EXPORT_URL, timeout=30, allow_redirects=True)
        reachable = r.status_code < 400
        status = r.status_code
    except requests.RequestException as exc:
        reachable = False
        status = str(exc)
    time.sleep(1)

    _save(
        "pandit",
        {"export_url": PANDIT_EXPORT_URL, "method": "CSV download (no count API)"},
        PANDIT_TOTAL_FROM_PAPER,
        notes=(
            f"Export endpoint reachable: {reachable} (HTTP {status}). "
            f"Total entities in published 2024-12-23 export: {PANDIT_TOTAL_FROM_PAPER:,} "
            "(source: Pāṇḍityatāraka, WSC 2025, Pāṇḍitya project paper). "
            "Karnataka-specific count requires downloading and filtering the CSV; "
            "that step is deferred to the connector."
        ),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Probe run: {date.today().isoformat()}")
    print(f"Results -> {RESULTS_DIR}")
    print(f"User-Agent: {USER_AGENT}")
    if ZENODO_API_KEY:
        print("Zenodo: authenticated (100 results/page, 60 req/min search limit)")
    else:
        print(
            "Zenodo: anonymous (25 results/page, 30 req/min search limit). "
            "Set ZENODO_API_KEY in .env for higher limits."
        )

    session = _session()

    print("\n--- counts ---")
    probe_wikidata(session)
    probe_mediawiki(session)
    probe_internet_archive(session)
    probe_siddham(session)
    probe_pandit(session)

    print(f"\nDone. Results saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
