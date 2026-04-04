"""
Generate QuickStatements for P13723 (shrine ranking) property work.

Phase 1: Add P459 (determination method or standard) qualifier to existing P13723 statements.
         Uses value-specific determination methods (Q712534 modern, Q138640329 Engishiki,
         Q135009120 Ritsuryō, etc.) based on the rank value.
Phase 2: Edit P13723 property definition (labels, constraints)
Phase 3: Migrate P31/P1552 shrine ranking values to P13723, preserving all
         existing qualifiers and references, and adding appropriate P459 qualifier.
Also:    Add Kokugakuin University references to Engishiki/Ritsuryō P13723 statements
         that currently lack sources.
"""

import io
import sys
import json
import os
import shutil
import time
import requests
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MAX_LINES_PER_BATCH = 200  # Budget ~200 QuickStatements per day per file

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}

# Phase 0: Property-level edits to P13723 itself
# Broadens P13723 from "modern shrine ranking" to general "shrine ranking"
PROPERTY_EDITS_FILE = "edit_p13723_property.txt"
# Property edits already applied — cleared 2026-03-29
PROPERTY_EDITS = []

# Build reverse mapping: rank value QID → determined_by QID
# Used by Phase 1 (P459 qualifiers) and reference correction to assign
# the correct determination method based on the rank value.
# Anything not in this mapping defaults to Q712534 (modern system).
RANK_VALUE_TO_P459 = {}  # populated from MIGRATIONS after definition

# Migration categories: old P31/P1552 values → P13723 with P459 qualifier
MIGRATIONS = [
    {
        "id": "engishiki",
        "name": "Engishiki ranking",
        "description": "Shikinai Shōsha, Shikinai Taisha, Myōjin Taisha",
        "source_property": "P31",
        "values": ["Q134917287", "Q134917288", "Q9610964"],
        "determined_by": "Q138640329",  # Engishiki ranking
        "output_file": "migrate_engishiki_ranking.txt",
        "reference_source": "kokugakuin",
    },
    {
        "id": "gifu",
        "name": "Gifu Prefecture Shrine ranking",
        "description": "Kinpei-sha, Ginpei-sha, Hakuhei-sha",
        "source_property": "P1552",
        "values": ["Q119929592", "Q137886068", "Q137886071"],
        "determined_by": "Q137901635",  # Gifu Prefecture Shrine ranking
        "output_file": "migrate_gifu_ranking.txt",
    },
    {
        "id": "beppyo",
        "name": "Beppyo Shrine",
        "description": "Beppyo Shrine",
        "source_property": "P31",
        "values": ["Q10898274"],
        "determined_by": "Q908077",  # Association of Shinto Shrines
        "output_file": "migrate_beppyo_shrine.txt",
        "reference_source": "jawiki",
    },
    {
        "id": "x_no_miya",
        "name": "X-no-miya",
        "description": "Ichinomiya, Ni-no-Miya, San-no-Miya, Shi-no-Miya, Go-no-Miya, Roku-no-Miya, Regional Ichinomiya",
        "source_property": "P31",
        "values": [
            "Q1656379",     # ichinomiya
            "Q134917290",   # Regional Ichinomiya
            "Q134917301",   # Go-no-Miya
            "Q134917303",   # San-no-Miya
            "Q134917307",   # Shi-no-Miya
            "Q134917533",   # Ni-no-Miya
            "Q135009625",   # Roku-no-Miya
        ],
        "determined_by": "Q134916677",  # X-no-miya
        "output_file": "migrate_x_no_miya.txt",
        "reference_source": "jawiki",
    },
    {
        "id": "ritsuryo",
        "name": "Ritsuryō funding type",
        "description": "Kokuhei-sha, Kanpei-sha, and ritual offering types",
        "source_property": "P31",
        "values": [
            "Q135160342",   # Kokuhei-sha
            "Q135160338",   # Kanpei-sha
            "Q135009152",   # Shrines receiving Hoe and Quiver
            "Q135009205",   # Shrines receiving Hoe offering
            "Q135009221",   # Shrines receiving Quiver offering
            "Q135009132",   # Shrines receiving Tsukinami-sai and Niiname-sai offerings
            "Q135009157",   # Shrines receiving Tsukinami-sai and Niiname-sai and Ainame-sai offerings
        ],
        "determined_by": "Q135009120",  # Ritsuryō funding type
        "output_file": "migrate_ritsuryo_funding.txt",
        "reference_source": "kokugakuin",
        # Remove P31=Kanpei-sha from items that have specific funding types
        # (per Wikidata bot request 2025-12-22)
        "underspecified_removal": {
            "condition_values": ["Q135009152", "Q135009205", "Q135009221", "Q135009132", "Q135009157"],
            "remove_value": "Q135160338",  # Kanpei-sha
            "remove_property": "P31",
        },
    },
]


# Populate the reverse mapping from MIGRATIONS
for _m in MIGRATIONS:
    for _v in _m["values"]:
        RANK_VALUE_TO_P459[_v] = _m["determined_by"]

# Engishiki + Ritsuryō values (for reference correction)
ENGISHIKI_RITSURYO_VALUES = set()
for _m in MIGRATIONS:
    if _m["id"] in ("engishiki", "ritsuryo"):
        ENGISHIKI_RITSURYO_VALUES.update(_m["values"])

ENGISHIKI_REFS_OUTPUT_FILE = "engishiki_add_references.txt"


class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests response is received."""


_last_sparql_time = 0.0


def fetch_sparql(query):
    """Run a SPARQL query against Wikidata with retry + exponential backoff on 429/timeout."""
    global _last_sparql_time
    max_retries = 4
    for attempt in range(max_retries + 1):
        # Throttle: at least 10s between SPARQL requests
        elapsed = time.time() - _last_sparql_time
        if elapsed < 10:
            time.sleep(10 - elapsed)
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=90,
            )
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as exc:
            _last_sparql_time = time.time()
            if attempt < max_retries:
                wait = 30 * (2 ** attempt)  # 30s, 60s, 120s, 240s
                print(f"SPARQL timeout/connection error — retrying in {wait}s (attempt {attempt + 1}/{max_retries}): {exc}", flush=True)
                time.sleep(wait)
                continue
            raise
        _last_sparql_time = time.time()
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt < max_retries:
                wait = 30 * (2 ** attempt)  # 30s, 60s, 120s, 240s
                print(f"{r.status_code} Server Error — retrying in {wait}s (attempt {attempt + 1}/{max_retries})", flush=True)
                time.sleep(wait)
                continue
            if r.status_code == 429:
                print(f"FATAL: 429 Too Many Requests after {max_retries} retries — bailing")
                raise RateLimitError(f"429 Too Many Requests: {r.url}")
            print(f"FATAL: {r.status_code} after {max_retries} retries — bailing")
            r.raise_for_status()
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def qid(uri):
    """Extract QID from Wikidata URI."""
    return uri.split("/")[-1]


def snak_to_qs(snak):
    """Convert a Wikidata API snak to QuickStatements v1 value format.

    Returns None for unsupported snak types.
    """
    snaktype = snak.get("snaktype", "value")
    if snaktype == "novalue":
        return "novalue"
    if snaktype == "somevalue":
        return "somevalue"
    if snaktype != "value":
        return None

    dv = snak["datavalue"]
    dtype = dv["type"]
    val = dv["value"]

    if dtype == "wikibase-entityid":
        return val["id"]
    if dtype == "string":
        return '"' + val.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if dtype == "time":
        return f'{val["time"]}/{val["precision"]}'
    if dtype == "quantity":
        amount = val["amount"]
        unit = val.get("unit", "")
        if unit and "entity/" in unit:
            return f'{amount}U{unit.split("/")[-1]}'
        return str(amount)
    if dtype == "monolingualtext":
        return f'{val["language"]}:"{val["text"]}"'
    if dtype == "globecoordinate":
        return f'@{val["latitude"]}/{val["longitude"]}'

    return None


def fetch_jawiki_sitelinks(item_ids):
    """Fetch Japanese Wikipedia sitelinks for items via the Wikidata API."""
    sitelinks = {}
    for i in range(0, len(item_ids), 50):
        batch = item_ids[i:i + 50]
        r = requests.get(
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "sitelinks",
                "sitefilter": "jawiki",
                "format": "json",
            },
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=120,
        )
        r.raise_for_status()
        entities = r.json().get("entities", {})
        for eid, entity in entities.items():
            jawiki = entity.get("sitelinks", {}).get("jawiki", {})
            if jawiki:
                title = jawiki["title"].replace(" ", "_")
                url = f"https://ja.wikipedia.org/wiki/{title}"
                sitelinks[eid] = ["S4656", f'"{url}"']
        if i + 50 < len(item_ids):
            time.sleep(1.5)
    return sitelinks


def claim_to_qs_lines(item_id, claim, determined_by, override_ref=None):
    """Convert a Wikidata claim to QS v1 lines migrating it to P13723.

    The new P13723 statement gets:
    - The original value
    - P459 (determination method or standard) qualifier with the appropriate ranking system
    - All original qualifiers preserved
    - References: either override_ref (if provided) or original references preserved

    Args:
        override_ref: Optional list of reference parts (e.g. ["S13677", '"123"', "S248", "Q135159299"])
                      to use instead of copying original references.
    """
    main_value = snak_to_qs(claim["mainsnak"])
    if not main_value:
        return []

    parts = [item_id, "P13723", main_value, "P459", determined_by]

    # Migrate all existing qualifiers
    qualifiers = claim.get("qualifiers", {})
    qual_order = claim.get("qualifiers-order", list(qualifiers.keys()))
    for prop in qual_order:
        for qsnak in qualifiers.get(prop, []):
            val = snak_to_qs(qsnak)
            if val is not None:
                parts.extend([prop, val])

    # Use override reference if provided
    if override_ref is not None:
        parts.extend(override_ref)
        return ["|".join(parts)]

    # Migrate references - each reference group becomes a separate QS line
    # First reference group goes on the main line, additional groups get their own lines
    references = claim.get("references", [])

    if references:
        # First reference on the main statement line
        ref = references[0]
        ref_order = ref.get("snaks-order", list(ref.get("snaks", {}).keys()))
        for prop in ref_order:
            for rsnak in ref["snaks"].get(prop, []):
                val = snak_to_qs(rsnak)
                if val is not None:
                    parts.extend([f"S{prop[1:]}", val])

    lines = ["|".join(parts)]

    # Additional reference groups as separate lines
    # These will create duplicate statements in QS v1 (limitation),
    # but it preserves all reference data for manual review
    for ref in references[1:]:
        ref_parts = [item_id, "P13723", main_value]
        ref_order = ref.get("snaks-order", list(ref.get("snaks", {}).keys()))
        has_refs = False
        for prop in ref_order:
            for rsnak in ref["snaks"].get(prop, []):
                val = snak_to_qs(rsnak)
                if val is not None:
                    ref_parts.extend([f"S{prop[1:]}", val])
                    has_refs = True
        if has_refs:
            lines.append("|".join(ref_parts))

    return lines


def fetch_claims_batch(item_ids, source_property):
    """Fetch claims for items from Wikidata API in batches of 50."""
    all_claims = {}
    for i in range(0, len(item_ids), 50):
        batch = item_ids[i:i + 50]
        r = requests.get(
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "claims",
                "format": "json",
            },
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=120,
        )
        r.raise_for_status()
        entities = r.json().get("entities", {})
        for eid, entity in entities.items():
            claims = entity.get("claims", {}).get(source_property, [])
            all_claims[eid] = claims
        if i + 50 < len(item_ids):
            time.sleep(1.5)
    return all_claims


HITEISHA_OUTPUT_FILE = "remove_shikinai_hiteisha.txt"


def generate_hiteisha_removals():
    """Generate QuickStatements to remove all P31=Q135026601 (Shikinai Hiteisha) statements."""
    query = """
    SELECT ?item WHERE {
      ?item wdt:P31 wd:Q135026601 .
    }
    ORDER BY ?item
    """

    total_query = """
    SELECT (COUNT(*) AS ?total) WHERE {
      ?item wdt:P31 wd:Q135026601 .
    }
    """

    print("\n=== Shikinai Hiteisha (Q135026601) removal ===")
    print("Fetching items with P31=Q135026601...")
    results = fetch_sparql(query)
    remaining = len(results)
    print(f"Found {remaining} items with P31=Shikinai Hiteisha to remove")

    lines = []
    for r in results:
        item = qid(r["item"]["value"])
        lines.append(f"-{item}|P31|Q135026601")

    with open(HITEISHA_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {HITEISHA_OUTPUT_FILE}")

    return {
        "name": "Remove P31 Shikinai Hiteisha",
        "description": "Remove all P31 (instance of) → Q135026601 (Shikinai Hiteisha) statements",
        "remaining": remaining,
        "output_file": HITEISHA_OUTPUT_FILE,
        "lines": len(lines),
    }


SHIKINAISHA_OUTPUT_FILE = "remove_shikinaisha.txt"


def generate_shikinaisha_removals():
    """Generate QuickStatements to remove P31=Q134917286 (Shikinaisha) from items that are P31=Q135022904 (Shikinai Ronsha)."""
    query = """
    SELECT ?item WHERE {
      ?item wdt:P31 wd:Q135022904 .
      ?item wdt:P31 wd:Q134917286 .
    }
    ORDER BY ?item
    """

    print("\n=== Shikinaisha (Q134917286) removal from Shikinai Ronsha items ===")
    print("Fetching Shikinai Ronsha items that also have P31=Shikinaisha...")
    results = fetch_sparql(query)
    remaining = len(results)
    print(f"Found {remaining} items with both P31=Shikinai Ronsha and P31=Shikinaisha")

    lines = []
    for r in results:
        item = qid(r["item"]["value"])
        lines.append(f"-{item}|P31|Q134917286")

    with open(SHIKINAISHA_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {SHIKINAISHA_OUTPUT_FILE}")

    return {
        "name": "Remove P31 Shikinaisha from Shikinai Ronsha",
        "description": "Remove P31 (instance of) → Q134917286 (Shikinaisha) from items that have P31=Q135022904 (Shikinai Ronsha)",
        "remaining": remaining,
        "output_file": SHIKINAISHA_OUTPUT_FILE,
        "lines": len(lines),
    }


def generate_property_edits():
    """Phase 0: Write property-level edits for P13723 itself."""
    print("\n=== Phase 2: P13723 property edits ===")
    with open(PROPERTY_EDITS_FILE, "w", encoding="utf-8") as f:
        for line in PROPERTY_EDITS:
            f.write(line + "\n")
    print(f"Written {len(PROPERTY_EDITS)} lines to {PROPERTY_EDITS_FILE}")
    return {
        "output_file": PROPERTY_EDITS_FILE,
        "lines": len(PROPERTY_EDITS),
    }


def generate_p459_qualifiers():
    """Phase 1: Add P459 qualifiers to existing P13723 statements.

    Uses RANK_VALUE_TO_P459 to assign the correct determination method
    based on the rank value (e.g. Engishiki ranks get Q138640329, Ritsuryō
    funding types get Q135009120, modern ranks get Q712534).
    """
    total_query = """
    SELECT (COUNT(*) AS ?total) WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
    }
    """
    remaining_query = """
    SELECT ?item ?rankvalue WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      FILTER NOT EXISTS { ?stmt pq:P459 ?_ }
    }
    ORDER BY ?item
    """

    print("=== Phase 1: P459 qualifiers ===")
    print("Fetching total P13723 statement count...")
    total = int(fetch_sparql(total_query)[0]["total"]["value"])
    print(f"Total P13723 statements: {total}")

    print("Fetching statements without P459 qualifier...")
    results = fetch_sparql(remaining_query)
    remaining = len(results)
    completed = total - remaining
    print(f"Found {remaining} to qualify ({completed}/{total} done)")

    output_file = "modern_shrine_ranking_qualifiers.txt"
    all_lines = []
    p459_counts = {}  # track how many get each P459
    for r in results:
        item = qid(r["item"]["value"])
        rankvalue = qid(r["rankvalue"]["value"])
        determined_by = RANK_VALUE_TO_P459.get(rankvalue, "Q712534")
        all_lines.append(f"{item}|P13723|{rankvalue}|P459|{determined_by}")
        p459_counts[determined_by] = p459_counts.get(determined_by, 0) + 1

    with open(output_file, "w", encoding="utf-8") as f:
        for line in all_lines:
            f.write(line + "\n")

    print(f"Written {len(all_lines)} lines to {output_file}")
    for db, count in sorted(p459_counts.items()):
        print(f"  P459={db}: {count} statements")

    return {
        "name": "P459 qualifiers (determination method)",
        "description": "Add P459 (determination method) to existing P13723 statements — value-specific (Engishiki, Ritsuryō, modern, etc.)",
        "total": total,
        "remaining": remaining,
        "completed": completed,
        "output_file": output_file,
        "lines": len(all_lines),
    }


P4656_OUTPUT_FILE = "p4656_jawiki_references.txt"


def generate_p4656_references():
    """Generate P4656 (Wikimedia import URL) references for all P13723 shrine rankings.

    Targets all P13723 statements that have a Japanese Wikipedia sitelink
    but no P4656 reference yet, regardless of determination method (P459).
    """
    query = """
    SELECT ?item ?rankvalue ?articleName WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      ?article schema:about ?item ;
               schema:isPartOf <https://ja.wikipedia.org/> ;
               schema:name ?articleName .
      FILTER NOT EXISTS {
        ?stmt prov:wasDerivedFrom ?ref .
        ?ref pr:P4656 ?_ .
      }
    }
    ORDER BY ?item
    """

    total_query = """
    SELECT (COUNT(*) AS ?total) WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
    }
    """

    print("\n=== P4656 Japanese Wikipedia references ===")
    print("Fetching total P13723 statements...")
    total = int(fetch_sparql(total_query)[0]["total"]["value"])
    print(f"Total P13723 statements: {total}")

    print("Fetching statements needing P4656 reference...")
    results = fetch_sparql(query)
    remaining = len(results)
    print(f"Found {remaining} statements with ja.wiki sitelink but no P4656 reference")

    lines = []
    for r in results:
        item = qid(r["item"]["value"])
        rankvalue = qid(r["rankvalue"]["value"])
        article_name = r["articleName"]["value"]
        # Use raw characters — percent-encoding breaks QuickStatements matching
        title = article_name.replace(" ", "_")
        url = f"https://ja.wikipedia.org/wiki/{title}"
        lines.append(f'{item}|P13723|{rankvalue}|S4656|"{url}"')

    with open(P4656_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {P4656_OUTPUT_FILE}")

    return {
        "name": "P4656 Japanese Wikipedia references",
        "description": "Add Wikimedia import URL (P4656) references pointing to ja.wikipedia for all P13723 statements",
        "total": total,
        "remaining": remaining,
        "completed": total - remaining,
        "output_file": P4656_OUTPUT_FILE,
        "lines": len(lines),
    }


def generate_engishiki_references():
    """Find P13723 statements with Engishiki/Ritsuryō rank values that lack references,
    and generate QuickStatements to add Kokugakuin University sources.

    Targets P13723 statements where:
    - The rank value is an Engishiki rank (Q134917287, Q134917288, Q9610964) or
      Ritsuryō funding type (Q135160342, Q135160338, Q135009152, etc.)
    - The statement has no reference at all
    - The item has a P13677 (Kokugakuin University Digital Museum entry ID)
    """
    values_sparql = " ".join(f"wd:{v}" for v in sorted(ENGISHIKI_RITSURYO_VALUES))

    # Find Engishiki/Ritsuryō P13723 statements without any reference
    query = f"""
    SELECT ?item ?rankvalue WHERE {{
      VALUES ?rankvalue {{ {values_sparql} }}
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      FILTER NOT EXISTS {{
        ?stmt prov:wasDerivedFrom ?ref .
      }}
    }}
    ORDER BY ?item
    """

    total_query = f"""
    SELECT (COUNT(*) AS ?total) WHERE {{
      VALUES ?rankvalue {{ {values_sparql} }}
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
    }}
    """

    print("\n=== Engishiki/Ritsuryō reference correction ===")
    print("Fetching total Engishiki/Ritsuryō P13723 statements...")
    total = int(fetch_sparql(total_query)[0]["total"]["value"])
    print(f"Total Engishiki/Ritsuryō P13723 statements: {total}")

    print("Fetching statements without references...")
    results = fetch_sparql(query)
    remaining = len(results)
    completed = total - remaining
    print(f"Found {remaining} without references ({completed}/{total} already sourced)")

    if not results:
        open(ENGISHIKI_REFS_OUTPUT_FILE, "w").close()
        print(f"Written 0 lines to {ENGISHIKI_REFS_OUTPUT_FILE}")
        return {
            "name": "Engishiki/Ritsuryō references",
            "description": "Add Kokugakuin University sources to Engishiki/Ritsuryō P13723 statements",
            "total": total,
            "remaining": 0,
            "completed": total,
            "output_file": ENGISHIKI_REFS_OUTPUT_FILE,
            "lines": 0,
            "skipped_no_p13677": 0,
        }

    # Collect unique items and their rank values
    items_values = {}
    for r in results:
        item_id = qid(r["item"]["value"])
        value_id = qid(r["rankvalue"]["value"])
        items_values.setdefault(item_id, set()).add(value_id)

    # Fetch P13677 for these items
    print(f"Fetching Kokugakuin University IDs (P13677) for {len(items_values)} items...")
    p13677_claims = fetch_claims_batch(list(items_values.keys()), "P13677")

    item_entry_ids = {}
    for item_id, claims in p13677_claims.items():
        if claims:
            val = snak_to_qs(claims[0]["mainsnak"])
            if val:
                item_entry_ids[item_id] = val

    print(f"  Found P13677 for {len(item_entry_ids)}/{len(items_values)} items")

    lines = []
    skipped_no_p13677 = 0
    for item_id, rank_values in sorted(items_values.items()):
        entry_id = item_entry_ids.get(item_id)
        if not entry_id:
            skipped_no_p13677 += 1
            continue
        for rv in sorted(rank_values):
            lines.append(
                f"{item_id}|P13723|{rv}|S248|Q135159299|S13677|{entry_id}"
            )

    with open(ENGISHIKI_REFS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {ENGISHIKI_REFS_OUTPUT_FILE}")
    if skipped_no_p13677:
        print(f"  Skipped {skipped_no_p13677} items (no P13677)")

    return {
        "name": "Engishiki/Ritsuryō references",
        "description": "Add Kokugakuin University sources to Engishiki/Ritsuryō P13723 statements",
        "total": total,
        "remaining": remaining,
        "completed": completed,
        "output_file": ENGISHIKI_REFS_OUTPUT_FILE,
        "lines": len(lines),
        "skipped_no_p13677": skipped_no_p13677,
    }


def generate_migration(migration):
    """Phase 3: Migrate P31/P1552 to P13723 with qualifiers and references.

    Generates two separate files:
    - ADD file: safe additions of P13723 statements (run first)
    - REMOVE file: removals of old source property statements (run only after adds are confirmed)
    """
    name = migration["name"]
    source_prop = migration["source_property"]
    values = migration["values"]
    determined_by = migration["determined_by"]
    output_file = migration["output_file"]
    # Derive add/remove filenames from the base output file
    base = output_file.rsplit(".", 1)[0]
    add_file = f"{base}_add.txt"
    remove_file = f"{base}_remove.txt"

    values_sparql = " ".join(f"wd:{v}" for v in values)

    # Count total statements (all items with this source property + values)
    total_query = f"""
    SELECT (COUNT(*) AS ?total) WHERE {{
      VALUES ?value {{ {values_sparql} }}
      ?item p:{source_prop} ?stmt .
      ?stmt ps:{source_prop} ?value .
    }}
    """

    # Find statements needing migration (no corresponding P13723 yet)
    # Uses MINUS instead of FILTER NOT EXISTS — the latter can return
    # phantom results on Wikidata's query service due to query optimizer
    # differences, producing thousands of false "remaining" items.
    remaining_query = f"""
    SELECT ?item ?value WHERE {{
      VALUES ?value {{ {values_sparql} }}
      ?item p:{source_prop} ?stmt .
      ?stmt ps:{source_prop} ?value .
      MINUS {{
        ?item p:P13723 ?s2 .
        ?s2 ps:P13723 ?value .
      }}
    }}
    ORDER BY ?item
    """

    # Find old statements safe to remove (P13723 already exists for this value)
    safe_remove_query = f"""
    SELECT ?item ?value WHERE {{
      VALUES ?value {{ {values_sparql} }}
      ?item p:{source_prop} ?stmt .
      ?stmt ps:{source_prop} ?value .
      ?item p:P13723 ?s2 .
      ?s2 ps:P13723 ?value .
    }}
    ORDER BY ?item
    """

    print(f"\n=== Migration: {name} ===")
    print("Fetching total count...")
    total = int(fetch_sparql(total_query)[0]["total"]["value"])

    print("Fetching items needing migration...")
    results = fetch_sparql(remaining_query)

    # Group by item → set of values to migrate
    items_values = {}
    for r in results:
        item_id = qid(r["item"]["value"])
        value_id = qid(r["value"]["value"])
        items_values.setdefault(item_id, set()).add(value_id)

    remaining = len(results)
    # total counts old statements still present; items whose old P31 was already
    # removed no longer appear.  Use remaining as the authoritative count of
    # work left, and derive a corrected total that is always >= remaining.
    completed = max(total - remaining, 0)
    corrected_total = completed + remaining
    print(f"{source_prop} → P13723: {remaining} to migrate ({completed}/{corrected_total} done)")

    if not items_values:
        open(add_file, "w").close()
    else:
        # Fetch full claim details from Wikidata API to get qualifiers + references
        print(f"Fetching claim details ({len(items_values)} items)...")
        all_claims = fetch_claims_batch(list(items_values.keys()), source_prop)

        # Fetch reference data based on reference_source
        ref_source = migration.get("reference_source")
        item_refs = {}
        if ref_source == "kokugakuin":
            print("Fetching Kokugakuin University IDs (P13677) for references...")
            p13677_claims = fetch_claims_batch(list(items_values.keys()), "P13677")
            for item_id, claims in p13677_claims.items():
                if claims:
                    val = snak_to_qs(claims[0]["mainsnak"])
                    if val:
                        item_refs[item_id] = ["S13677", val, "S248", "Q135159299"]
            print(f"  Found P13677 for {len(item_refs)}/{len(items_values)} items")
        elif ref_source == "jawiki":
            print("Fetching Japanese Wikipedia sitelinks for references...")
            item_refs = fetch_jawiki_sitelinks(list(items_values.keys()))
            print(f"  Found jawiki sitelinks for {len(item_refs)}/{len(items_values)} items")

        # For P31 migrations, check which items already have P31=Q845945 (Shinto shrine)
        # so we can add it before removing the old P31 value
        items_have_shinto_shrine = set()
        if source_prop == "P31":
            for item_id, claims in all_claims.items():
                for claim in claims:
                    cv = snak_to_qs(claim["mainsnak"])
                    if cv == "Q845945":
                        items_have_shinto_shrine.add(item_id)

        # Generate ADD lines only (safe to run)
        add_lines = []
        items_given_shinto_shrine = set()
        for item_id, target_values in sorted(items_values.items()):
            for claim in all_claims.get(item_id, []):
                cv = snak_to_qs(claim["mainsnak"])
                if cv in target_values:
                    if source_prop == "P31" and item_id not in items_have_shinto_shrine and item_id not in items_given_shinto_shrine:
                        add_lines.append(f"{item_id}|P31|Q845945")
                        items_given_shinto_shrine.add(item_id)
                    # Use override reference if available for this item
                    override_ref = item_refs.get(item_id) if ref_source else None
                    add_lines.extend(claim_to_qs_lines(item_id, claim, determined_by, override_ref=override_ref))

        with open(add_file, "w", encoding="utf-8") as f:
            for line in add_lines:
                f.write(line + "\n")
        print(f"Written {len(add_lines)} ADD lines to {add_file}")

    # Generate REMOVE lines (only for items where P13723 already exists)
    print("Fetching statements safe to remove (P13723 already confirmed)...")
    safe_results = fetch_sparql(safe_remove_query)
    remove_lines = []
    for r in safe_results:
        item_id = qid(r["item"]["value"])
        value_id = qid(r["value"]["value"])
        remove_lines.append(f"-{item_id}|{source_prop}|{value_id}")

    with open(remove_file, "w", encoding="utf-8") as f:
        for line in remove_lines:
            f.write(line + "\n")
    print(f"Written {len(remove_lines)} REMOVE lines to {remove_file}")

    # Handle underspecified removals (e.g., remove P31=Kanpei-sha from items
    # that have more specific funding types, per bot request pattern)
    underspec = migration.get("underspecified_removal")
    underspec_lines = 0
    underspec_file = None
    if underspec:
        condition_values = underspec["condition_values"]
        remove_value = underspec["remove_value"]
        remove_prop = underspec.get("remove_property", "P31")
        cond_sparql = " ".join(f"wd:{v}" for v in condition_values)

        uquery = f"""
        SELECT DISTINCT ?item WHERE {{
          VALUES ?condValue {{ {cond_sparql} }}
          ?item wdt:{remove_prop} ?condValue .
          ?item wdt:{remove_prop} wd:{remove_value} .
        }}
        ORDER BY ?item
        """

        print(f"Fetching items for underspecified removal ({remove_prop}={remove_value})...")
        uresults = fetch_sparql(uquery)
        ulines = []
        for r in uresults:
            item_id = qid(r["item"]["value"])
            ulines.append(f"-{item_id}|{remove_prop}|{remove_value}")

        underspec_file = f"{base}_underspecified_remove.txt"
        with open(underspec_file, "w", encoding="utf-8") as f:
            for line in ulines:
                f.write(line + "\n")
        underspec_lines = len(ulines)
        print(f"Written {underspec_lines} underspecified removal lines to {underspec_file}")

    return {
        "name": name,
        "description": migration["description"],
        "source_property": source_prop,
        "determined_by": determined_by,
        "total": corrected_total,
        "remaining": remaining,
        "completed": completed,
        "add_file": add_file,
        "remove_file": remove_file,
        "add_lines": len(add_lines) if items_values else 0,
        "remove_lines": len(remove_lines),
        "underspec_file": underspec_file,
        "underspec_lines": underspec_lines,
    }


def read_first_n_lines(filepath, n=MAX_LINES_PER_BATCH):
    """Read the first n lines from a file, return them as a single string."""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i >= n:
                break
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def html_escape(text):
    """Escape text for safe embedding in HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load_p958_summary():
    """Load P958 summary JSON if it exists."""
    path = "p958_summary.json"
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_p958_html_section(summary):
    """Generate HTML section for P958 qualifier work."""
    if not summary:
        return ""

    total = summary["generated"] + summary["completed"]
    completed = summary["completed"]
    pct = completed * 100 // total if total > 0 else 0

    # Read the QuickStatements for the copy-paste box
    qs_batch = read_first_n_lines(summary["output_file"])
    qs_escaped = html_escape(qs_batch)

    # Build manual review table
    manual_rows = ""
    for item in summary.get("manual_review_items", []):
        parts = item.split("\t")
        if len(parts) >= 6:
            qid, label, parent, ranking, count, link_type = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            manual_rows += f"<tr><td><a href=\"https://www.wikidata.org/wiki/{qid}\">{qid}</a></td><td>{html_escape(label)}</td><td>{html_escape(parent)}</td><td>{ranking}</td><td>{count}</td><td>{link_type}</td></tr>\n"

    manual_table = ""
    if manual_rows:
        manual_table = f"""
    <details>
      <summary><strong>{summary["manual_review"]} items need manual review</strong> (multiple P13677 statements)</summary>
      <table border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem;">
        <tr><th>QID</th><th>Label</th><th>Parent</th><th>Ranking</th><th>P13677 count</th><th>Link type</th></tr>
        {manual_rows}
      </table>
    </details>"""

    # Build sequence anomaly table
    anomaly_list = ""
    if summary.get("sequence_anomaly_items"):
        anomaly_rows = ""
        for a in summary["sequence_anomaly_items"]:
            if isinstance(a, dict):
                qid = a["qid"]
                label = html_escape(a["label"])
                rankings = ", ".join(str(r) for r in a["rankings"])
                expected = ", ".join(str(r) for r in a["expected"])
            else:
                # Legacy string format fallback
                qid = a.strip().split(" ")[0]
                label = html_escape(a.strip())
                rankings = ""
                expected = ""
            anomaly_rows += (
                f'<tr><td><a href="https://www.wikidata.org/wiki/{qid}">{qid}</a></td>'
                f'<td>{label}</td><td>{rankings}</td><td>{expected}</td></tr>\n'
            )
        anomaly_list = f"""
    <details>
      <summary><strong>{summary["sequence_anomalies"]} ranking sequence anomalies</strong></summary>
      <table border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem;">
        <tr><th>QID</th><th>Label</th><th>Actual rankings</th><th>Expected rankings</th></tr>
        {anomaly_rows}
      </table>
    </details>"""

    shown = min(summary["generated"], MAX_LINES_PER_BATCH)

    return f"""
  <h2>P958: Kokugakuin Museum Entry ID Section Qualifiers</h2>
  <p>Add <code>P958</code> (section) qualifiers to <code>P13677</code> (Kokugakuin University Digital Museum entry ID)
     on Ronsha items, based on <code>P1352</code> (ranking) qualifiers from Shikinaisha
     <code>P527</code>/<code>P460</code> links.</p>
  <div class="stats">
    <strong>{completed} / {total} done</strong> ({pct}%)
    &mdash; <strong>{summary["generated"]} remaining</strong>
    &mdash; {summary["skipped_no_p13677"]} skipped (no P13677)
    <div class="progress-bar">
      <div class="progress-fill" style="width: {max(pct, 2 if completed else 0)}%">{pct}%</div>
    </div>
  </div>
  <p>Today's batch: {shown} of {summary["generated"]} total lines
     &mdash; <a href="{summary["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{qs_escaped}</textarea>
  {manual_table}
  {anomaly_list}"""


def fetch_duplicate_items(prop):
    """Fetch Shikinai Ronsha items with duplicate statements for a property."""
    query = f"""
    SELECT ?item ?itemLabel (COUNT(?s) AS ?count) WHERE {{
      ?item wdt:P31 wd:Q135022904 .
      ?item p:{prop} ?s .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja" }}
    }} GROUP BY ?item ?itemLabel HAVING(COUNT(?s) > 1) ORDER BY DESC(?count)
    """
    try:
        results = fetch_sparql(query)
        items = []
        for row in results:
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            label = row.get("itemLabel", {}).get("value", qid)
            count = int(row["count"]["value"])
            items.append({"qid": qid, "label": label, "count": count})
        return items
    except Exception as e:
        print(f"  Warning: failed to fetch {prop} duplicates: {e}")
        return []


def generate_duplicates_section():
    """Fetch and render the duplicate properties section."""
    print("\n=== Fetching duplicate property data ===")

    dupes = {}
    for prop in ["P361", "P1448", "P6375"]:
        print(f"  Querying {prop} duplicates...")
        dupes[prop] = fetch_duplicate_items(prop)
        print(f"    Found {len(dupes[prop])} items with duplicate {prop}")
        time.sleep(2)

    def item_list_html(items):
        if not items:
            return "<p><em>No duplicates found (or query failed).</em></p>"
        rows = ""
        for item in items:
            rows += (
                f'<li><a href="https://www.wikidata.org/wiki/{item["qid"]}">'
                f'{item["qid"]}</a> {html_escape(item["label"])} '
                f'({item["count"]} statements)</li>\n'
            )
        return f'<ul style="font-size: 0.85rem; max-height: 300px; overflow-y: auto;">{rows}</ul>'

    p361_list = item_list_html(dupes["P361"])
    p1448_list = item_list_html(dupes["P1448"])
    p6375_list = item_list_html(dupes["P6375"])

    return f"""
  <h2>Duplicate Properties on Shikinai Ronsha</h2>
  <p>Due to a partial data migration that broke provenance, many
     <a href="https://www.wikidata.org/wiki/Q135022904">Shikinai Ronsha</a> items
     ended up with duplicate <code>P361</code>, <code>P1448</code>, and <code>P6375</code>
     statements. The original source had bad data modelling, and correcting it in a way
     that broke provenance made the situation worse.</p>

  <div class="category">
    <h3>P361 (part of) &mdash; {len(dupes["P361"])} items with duplicates</h3>
    <p class="desc">These duplicates are related to ordering in the Engishiki lists.
      The P361 and P1448 properties on these items tend to be highly property-heavy
      (many qualifiers and references). We could probably fix the P361 duplicates by
      walking through the lists again and reconciling.</p>
    <details>
      <summary>Show all {len(dupes["P361"])} items</summary>
      {p361_list}
    </details>
  </div>

  <div class="category">
    <h3>P1448 (official name) &mdash; {len(dupes["P1448"])} items with duplicates</h3>
    <p class="desc">Like P361, these tend to be property-heavy items. The incorrect
      P1448 statements appear to be directly detectable by checking their source
      references &mdash; the wrong ones will have mismatched or missing sources.</p>
    <details>
      <summary>Show all {len(dupes["P1448"])} items</summary>
      {p1448_list}
    </details>
  </div>

  <div class="category">
    <h3>P6375 (street address) &mdash; {len(dupes["P6375"])} items with duplicates</h3>
    <p class="desc">These are simpler duplicates compared to P361/P1448. Someone other
      than the original importer would be best to assess which addresses are correct,
      as the duplicates may reflect genuinely different locations for merged items.</p>
    <details>
      <summary>Show all {len(dupes["P6375"])} items</summary>
      {p6375_list}
    </details>
  </div>

  <p class="desc">Example of all three issues on a single item:
     <a href="https://www.wikidata.org/wiki/Q59282644">Q59282644</a> (Takagi Shrine)</p>"""


def generate_hiteisha_html_section(stats):
    """Generate HTML section for Shikinai Hiteisha removal."""
    if not stats or stats["lines"] == 0:
        return """
  <h2>Remove P31 Shikinai Hiteisha (Q135026601)</h2>
  <p>All <code>P31</code> &rarr; <code>Q135026601</code> (Shikinai Hiteisha) statements have been removed.</p>
  <div class="stats"><strong>0 remaining</strong></div>"""

    batch = read_first_n_lines(stats["output_file"])
    batch_escaped = html_escape(batch)
    shown = min(stats["lines"], MAX_LINES_PER_BATCH)

    return f"""
  <h2>Remove P31 Shikinai Hiteisha (Q135026601)</h2>
  <p>Remove all <code>P31</code> (instance of) &rarr; <code>Q135026601</code>
     (<a href="https://www.wikidata.org/wiki/Q135026601">Shikinai Hiteisha</a>) statements.
     This class is being deprecated and should be removed from all items.</p>
  <div class="stats">
    <strong>{stats["remaining"]} items remaining</strong>
  </div>
  <p>{shown} of {stats["lines"]} total lines
     &mdash; <a href="{stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{batch_escaped}</textarea>"""


def generate_shikinaisha_html_section(stats):
    """Generate HTML section for Shikinaisha removal from Shikinai Ronsha items."""
    if not stats or stats["lines"] == 0:
        return """
  <h2>Remove P31 Shikinaisha (Q134917286) from Shikinai Ronsha</h2>
  <p>All <code>P31</code> &rarr; <code>Q134917286</code> (Shikinaisha) statements have been removed from Shikinai Ronsha items.</p>
  <div class="stats"><strong>0 remaining</strong></div>"""

    batch = read_first_n_lines(stats["output_file"])
    batch_escaped = html_escape(batch)
    shown = min(stats["lines"], MAX_LINES_PER_BATCH)

    return f"""
  <h2>Remove P31 Shikinaisha (Q134917286) from Shikinai Ronsha</h2>
  <p>Remove <code>P31</code> (instance of) &rarr; <code>Q134917286</code>
     (<a href="https://www.wikidata.org/wiki/Q134917286">Shikinaisha</a>) from items that have
     <code>P31</code> &rarr; <code>Q135022904</code>
     (<a href="https://www.wikidata.org/wiki/Q135022904">Shikinai Ronsha</a>).
     Shikinai Ronsha is more specific and replaces the generic Shikinaisha class.</p>
  <div class="stats">
    <strong>{stats["remaining"]} items remaining</strong>
  </div>
  <p>{shown} of {stats["lines"]} total lines
     &mdash; <a href="{stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{batch_escaped}</textarea>"""


def generate_p11250_html_section():
    """Generate HTML section for P11250 Miraheze article ID lines."""
    p11250_file = "p11250_miraheze_links.txt"
    if not os.path.exists(p11250_file):
        return ""

    with open(p11250_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return """
  <h2>P11250 Miraheze Article ID</h2>
  <p>All Wikidata items are linked to their shintowiki pages.</p>
  <div class="stats"><strong>0 remaining</strong></div>"""

    batch = "\n".join(lines[:MAX_LINES_PER_BATCH])
    batch_escaped = html_escape(batch)
    shown = min(len(lines), MAX_LINES_PER_BATCH)

    return f"""
  <h2>P11250 Miraheze Article ID</h2>
  <p>Add <code>P11250</code> (Miraheze article ID) linking Wikidata items to their corresponding
     pages on <a href="https://shinto.miraheze.org">shinto.miraheze.org</a>.</p>
  <div class="stats">
    <strong>{len(lines)} items remaining</strong>
  </div>
  <p>{shown} of {len(lines)} total lines
     &mdash; <a href="{p11250_file}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{batch_escaped}</textarea>"""


def generate_html(p459_stats, migration_stats, prop_stats, hiteisha_stats=None, engishiki_refs_stats=None, shikinaisha_stats=None):
    """Generate the site index.html with progress for all categories."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def progress_pct(completed, total):
        return completed * 100 // total if total > 0 else 100

    p459_pct = progress_pct(p459_stats["completed"], p459_stats["total"])

    # Read first 200 lines for copy-paste boxes
    p459_batch = read_first_n_lines(p459_stats["output_file"])
    p459_batch_escaped = html_escape(p459_batch)

    # P958 section from separate generator
    p958_summary = load_p958_summary()
    p958_section = generate_p958_html_section(p958_summary)

    # Engishiki/Ritsuryō reference correction section
    engishiki_refs_section = ""
    if engishiki_refs_stats and engishiki_refs_stats.get("lines", 0) > 0:
        er = engishiki_refs_stats
        er_pct = progress_pct(er["completed"], er["total"])
        er_batch = read_first_n_lines(er["output_file"])
        er_escaped = html_escape(er_batch)
        er_shown = min(er["lines"], MAX_LINES_PER_BATCH)
        engishiki_refs_section = f"""
  <h2>Engishiki/Ritsury&#x14D; Reference Correction</h2>
  <p>Add <a href="https://www.wikidata.org/wiki/Q135159299">Kokugakuin University</a> sources
     (<code>S248</code> + <code>S13677</code>) to <code>P13723</code> statements with
     Engishiki ranking or Ritsury&#x14D; funding values that currently have no references.</p>
  <div class="stats">
    <strong>{er["completed"]} / {er["total"]} sourced</strong> ({er_pct}%)
    &mdash; <strong>{er["remaining"]} without references</strong>
    {"&mdash; " + str(er.get("skipped_no_p13677", 0)) + " skipped (no P13677)" if er.get("skipped_no_p13677") else ""}
    <div class="progress-bar">
      <div class="progress-fill" style="width: {max(er_pct, 2 if er['completed'] else 0)}%">{er_pct}%</div>
    </div>
  </div>
  <p>{er_shown} of {er["lines"]} total lines
     &mdash; <a href="{er["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{er_escaped}</textarea>"""
    elif engishiki_refs_stats:
        engishiki_refs_section = """
  <h2>Engishiki/Ritsury&#x14D; Reference Correction</h2>
  <p>All Engishiki/Ritsury&#x14D; <code>P13723</code> statements are sourced.</p>
  <div class="stats"><strong>0 remaining</strong></div>"""

    # Shikinai Hiteisha removal section
    hiteisha_section = generate_hiteisha_html_section(hiteisha_stats) if hiteisha_stats else ""
    shikinaisha_section = generate_shikinaisha_html_section(shikinaisha_stats) if shikinaisha_stats else ""
    p11250_section = generate_p11250_html_section()

    # Duplicate properties section
    duplicates_section = generate_duplicates_section()

    migration_sections = ""
    for m in migration_stats:
        pct = progress_pct(m["completed"], m["total"])
        add_batch = read_first_n_lines(m["add_file"])
        add_escaped = html_escape(add_batch)
        add_shown = min(m["add_lines"], MAX_LINES_PER_BATCH)
        remove_batch = read_first_n_lines(m["remove_file"])
        remove_escaped = html_escape(remove_batch)
        remove_shown = min(m["remove_lines"], MAX_LINES_PER_BATCH)

        # Underspecified removal section (e.g., remove Kanpei-sha from items with specific types)
        underspec_section = ""
        if m.get("underspec_file") and m.get("underspec_lines", 0) > 0:
            underspec_batch = read_first_n_lines(m["underspec_file"])
            underspec_escaped = html_escape(underspec_batch)
            underspec_shown = min(m["underspec_lines"], MAX_LINES_PER_BATCH)
            underspec_section = f"""
      <h4>Step 3: Remove underspecified types (safe to run independently)</h4>
      <p>{underspec_shown} of {m["underspec_lines"]} total lines
         &mdash; <a href="{m["underspec_file"]}">Download all</a></p>
      <textarea class="qs-box" rows="6" readonly onclick="this.select()">{underspec_escaped}</textarea>"""

        migration_sections += f"""
    <div class="category">
      <h3>{m["name"]}</h3>
      <p class="desc">{m["description"]}<br>
        <code>{m["source_property"]}</code> &rarr; <code>P13723</code>
        &nbsp;|&nbsp; qualifier <code>P459</code> &rarr; <code>{m["determined_by"]}</code></p>
      <div class="stats">
        <strong>{m["completed"]} / {m["total"]} migrated</strong> ({pct}%)
        &mdash; <strong>{m["remaining"]} remaining</strong>
        <div class="progress-bar">
          <div class="progress-fill" style="width: {max(pct, 2)}%">{pct}%</div>
        </div>
      </div>
      <h4>Step 1: Add P13723 statements (safe to run)</h4>
      <p>{add_shown} of {m["add_lines"]} total lines
         &mdash; <a href="{m["add_file"]}">Download all</a></p>
      <textarea class="qs-box" rows="10" readonly onclick="this.select()">{add_escaped}</textarea>
      <h4>Step 2: Remove old {m["source_property"]} statements (only after Step 1 is confirmed)</h4>
      <p>{remove_shown} of {m["remove_lines"]} total lines
         &mdash; <a href="{m["remove_file"]}">Download all</a></p>
      <textarea class="qs-box" rows="6" readonly onclick="this.select()">{remove_escaped}</textarea>
      {underspec_section}
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Shrine Ranking (P13723) - QuickStatements</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #333; }}
    h1 {{ border-bottom: 2px solid #4caf50; padding-bottom: 0.5rem; }}
    h2 {{ margin-top: 2rem; color: #2e7d32; }}
    h3 {{ margin-bottom: 0.25rem; }}
    pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; font-size: 0.85rem; border-radius: 4px; }}
    a {{ color: #0645ad; }}
    code {{ background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }}
    .stats {{ background: #e8f4e8; padding: 1rem; border-radius: 4px; margin: 0.75rem 0; }}
    .progress-bar {{ background: #ddd; border-radius: 8px; overflow: hidden; height: 24px; margin: 0.5rem 0; display: flex; }}
    .progress-fill {{ background: #4caf50; height: 100%; text-align: center; color: white;
                      font-size: 0.85rem; line-height: 24px;
                      transition: width 0.3s ease; }}
    .progress-fill:not(:empty) {{ min-width: 2rem; }}
    .category {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }}
    .desc {{ color: #666; margin: 0.25rem 0 0.75rem; font-size: 0.95rem; }}
    .timestamp {{ color: #888; font-size: 0.85rem; }}
    .instructions {{ background: #fff3e0; padding: 1rem; border-radius: 4px; margin: 1rem 0;
                     border-left: 4px solid #ff9800; }}
    .qs-box {{ width: 100%; font-family: monospace; font-size: 0.8rem; background: #f5f5f5;
               border: 1px solid #ccc; border-radius: 4px; padding: 0.5rem; resize: vertical; }}
  </style>
</head>
<body>
  <h1>Shrine Ranking (P13723) &mdash; QuickStatements</h1>
  <p class="timestamp">Last updated: {generated}
    &mdash; <a href="https://github.com/EmmaLeonhart/shintowiki-scripts">Source on GitHub</a></p>

  <div class="instructions" style="background: #e3f2fd; border-left-color: #2196f3;">
    <strong><a href="daily.html" style="font-size: 1.1em;">Daily Operations &rarr;</a></strong>
    &mdash; Single combined box of everything to paste right now. Just keep running it.
  </div>

  <div class="instructions">
    <strong>How to use:</strong> Click a text box below to select its contents, then paste into
    <a href="https://quickstatements.toolforge.org/#/batch">QuickStatements</a>.
    Each box shows up to {MAX_LINES_PER_BATCH} lines (~1 day's budget). Full files available via download links.
    Run in order: Phase 1 (add P459), then Phase 2, then each migration.
  </div>

  <h2>Phase 1: Add P459 qualifiers to existing P13723</h2>
  <p>Add <code>P459</code> (determination method or standard) to all existing <code>P13723</code> statements.
     Each rank value gets the correct determination method: <code>Q712534</code> (modern),
     <code>Q138640329</code> (Engishiki), <code>Q135009120</code> (Ritsury&#x14D;), etc.</p>
  <div class="stats">
    <strong>{p459_stats["completed"]} / {p459_stats["total"]} done</strong> ({p459_pct}%)
    &mdash; <strong>{p459_stats["remaining"]} remaining</strong>
    <div class="progress-bar">
      <div class="progress-fill" style="width: {max(p459_pct, 2 if p459_stats['completed'] else 0)}%">{p459_pct}%</div>
    </div>
  </div>
  <p>Today's batch: {min(p459_stats.get("lines", p459_stats["remaining"]), MAX_LINES_PER_BATCH)} of {p459_stats.get("lines", p459_stats["remaining"])} total lines
     &mdash; <a href="{p459_stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{p459_batch_escaped}</textarea>

  <h2>Migrate old properties to P13723</h2>
  <p>Migrate <code>P31</code> / <code>P1552</code> shrine ranking values to <code>P13723</code>,
     preserving all existing qualifiers and references, and adding the appropriate
     <code>P459</code> (determination method or standard) qualifier.</p>
  {migration_sections}

  {p958_section}

  {engishiki_refs_section}

  {hiteisha_section}

  {shikinaisha_section}

  {p11250_section}

  {duplicates_section}

  <hr>
  <p class="timestamp">Generated automatically from SPARQL + Wikidata API data.</p>
</body>
</html>"""

    os.makedirs("_site", exist_ok=True)
    with open("_site/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_daily_operations(p459_stats, prop_stats, migration_stats, p4656_stats, hiteisha_stats=None, engishiki_refs_stats=None, shikinaisha_stats=None):
    """Generate the daily operations page — a single combined box of what to run now.

    Priority order:
    - Phase 1 (P459 qualifiers) until complete
    - Phase 2 (property edits) after Phase 1 complete
    - P4656 references (always included when lines exist)
    - Phase 3 (migration adds + removes) after Phase 2 complete
    - P958 qualifiers always included
    - Engishiki/Ritsuryō references always included
    - Shikinai Hiteisha removals always included
    """
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    phase_description = ""

    p1_done = p459_stats["remaining"] == 0

    if not p1_done:
        # Phase 1 not complete — include P459 lines
        phase_description = "Phase 1: Adding P459 qualifiers to existing P13723 statements"
        p459_file = p459_stats["output_file"]
        if os.path.exists(p459_file):
            with open(p459_file, "r", encoding="utf-8") as f:
                lines.extend(line.strip() for line in f if line.strip())
    elif prop_stats["lines"] > 0:
        # Phase 1 complete, Phase 2 not done — include property edits
        phase_description = "Phase 2: Editing P13723 property definition"
        prop_file = prop_stats["output_file"]
        if os.path.exists(prop_file):
            with open(prop_file, "r", encoding="utf-8") as f:
                lines.extend(line.strip() for line in f if line.strip())
    else:
        # Phase 1 and 2 complete — include all migration adds and removes
        phase_description = "Phase 3: Migrating old properties to P13723"
        for m in migration_stats:
            for fpath in [m["add_file"], m["remove_file"]]:
                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8") as f:
                        lines.extend(line.strip() for line in f if line.strip())
            # Include underspecified removal lines
            if m.get("underspec_file") and os.path.exists(m["underspec_file"]):
                with open(m["underspec_file"], "r", encoding="utf-8") as f:
                    lines.extend(line.strip() for line in f if line.strip())

    # Always include P4656 Japanese Wikipedia references
    p4656_count = 0
    p4656_file = p4656_stats["output_file"]
    if os.path.exists(p4656_file):
        with open(p4656_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    p4656_count += 1

    # Always include P958 qualifiers
    p958_file = "p958_qualifiers.txt"
    p958_count = 0
    if os.path.exists(p958_file):
        with open(p958_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    p958_count += 1

    # Always include Engishiki/Ritsuryō reference corrections
    engishiki_refs_count = 0
    if engishiki_refs_stats and os.path.exists(engishiki_refs_stats["output_file"]):
        with open(engishiki_refs_stats["output_file"], "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    engishiki_refs_count += 1

    # Always include Shikinai Hiteisha removals
    hiteisha_count = 0
    if hiteisha_stats and os.path.exists(hiteisha_stats["output_file"]):
        with open(hiteisha_stats["output_file"], "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    hiteisha_count += 1

    # Always include Shikinaisha removals (from Shikinai Ronsha items)
    shikinaisha_count = 0
    if shikinaisha_stats and os.path.exists(shikinaisha_stats["output_file"]):
        with open(shikinaisha_stats["output_file"], "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    shikinaisha_count += 1

    # Always include P11250 Miraheze article ID lines
    p11250_count = 0
    p11250_file = "p11250_miraheze_links.txt"
    if os.path.exists(p11250_file):
        with open(p11250_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    p11250_count += 1

    # Write combined file
    daily_file = "daily_operations.txt"
    with open(daily_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    batch_text = "\n".join(lines[:MAX_LINES_PER_BATCH])
    batch_escaped = html_escape(batch_text)
    shown = min(len(lines), MAX_LINES_PER_BATCH)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Operations - QuickStatements</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #333; }}
    h1 {{ border-bottom: 2px solid #4caf50; padding-bottom: 0.5rem; }}
    a {{ color: #0645ad; }}
    code {{ background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }}
    .instructions {{ background: #fff3e0; padding: 1rem; border-radius: 4px; margin: 1rem 0;
                     border-left: 4px solid #ff9800; }}
    .stats {{ background: #e8f4e8; padding: 1rem; border-radius: 4px; margin: 0.75rem 0; }}
    .timestamp {{ color: #888; font-size: 0.85rem; }}
    .qs-box {{ width: 100%; font-family: monospace; font-size: 0.8rem; background: #f5f5f5;
               border: 1px solid #ccc; border-radius: 4px; padding: 0.5rem; resize: vertical; }}
  </style>
</head>
<body>
  <h1>Daily Operations</h1>
  <p class="timestamp">Last updated: {generated}</p>
  <p><a href="index.html">&larr; Back to full dashboard</a></p>

  <div class="instructions">
    <strong>Paste everything below into
    <a href="https://quickstatements.toolforge.org/#/batch">QuickStatements</a>.</strong>
    Most batches will fail &mdash; that is expected. Just keep running them.
    Completed statements are automatically excluded on the next generation.
  </div>

  <div class="stats">
    <strong>Current phase:</strong> {phase_description}<br>
    <strong>{len(lines)} total lines</strong> (showing first {shown})
    &mdash; <a href="daily_operations.txt">Download all</a><br>
    {"<em>Includes " + str(p4656_count) + " P4656 ja.wiki reference lines</em><br>" if p4656_count else ""}
    {"<em>Includes " + str(p958_count) + " P958 qualifier lines</em><br>" if p958_count else ""}
    {"<em>Includes " + str(engishiki_refs_count) + " Engishiki/Ritsury&#x14D; reference lines</em><br>" if engishiki_refs_count else ""}
    {"<em>Includes " + str(hiteisha_count) + " Shikinai Hiteisha removal lines</em><br>" if hiteisha_count else ""}
    {"<em>Includes " + str(shikinaisha_count) + " Shikinaisha removal lines (from Shikinai Ronsha)</em><br>" if shikinaisha_count else ""}
    {"<em>Includes " + str(p11250_count) + " P11250 Miraheze article ID lines</em>" if p11250_count else ""}
  </div>

  <textarea class="qs-box" rows="30" readonly onclick="this.select()">{batch_escaped}</textarea>

  <hr>
  <p class="timestamp">Generated automatically from SPARQL + Wikidata API data.</p>
</body>
</html>"""

    with open(os.path.join("_site", "daily.html"), "w", encoding="utf-8") as f:
        f.write(html)
    shutil.copy(daily_file, os.path.join("_site", daily_file))
    print(f"Daily operations: {len(lines)} lines ({phase_description})")


def main():
    rate_limited = False

    # Phase 1: P459 qualifiers for existing P13723 statements
    try:
        p459_stats = generate_p459_qualifiers()
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during P459 phase, skipping remaining work", flush=True)
        p459_stats = {"output_file": "modern_shrine_ranking_qualifiers.txt", "added": 0, "skipped": 0, "total": 0}
        rate_limited = True

    # Phase 2: Property-level edits to P13723 (after modern qualifiers, before migrations)
    try:
        prop_stats = generate_property_edits() if not rate_limited else {"output_file": "edit_p13723_property.txt", "lines": 0}
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during property edits phase, skipping", flush=True)
        prop_stats = {"output_file": "edit_p13723_property.txt", "lines": 0}
        rate_limited = True

    # Remove P31=Q135026601 (Shikinai Hiteisha) statements
    try:
        hiteisha_stats = generate_hiteisha_removals() if not rate_limited else {"output_file": "remove_shikinai_hiteisha.txt", "removed": 0, "total": 0}
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during hiteisha removals, skipping", flush=True)
        hiteisha_stats = {"output_file": "remove_shikinai_hiteisha.txt", "removed": 0, "total": 0}
        rate_limited = True

    # Remove P31=Q134917286 (Shikinaisha) from Shikinai Ronsha items
    try:
        shikinaisha_stats = generate_shikinaisha_removals() if not rate_limited else {"output_file": "remove_shikinaisha.txt", "remaining": 0, "lines": 0}
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during shikinaisha removals, skipping", flush=True)
        shikinaisha_stats = {"output_file": "remove_shikinaisha.txt", "remaining": 0, "lines": 0}
        rate_limited = True

    # P4656: Add Japanese Wikipedia references to all P13723 statements
    try:
        p4656_stats = generate_p4656_references() if not rate_limited else {"output_file": "add_p4656_jawiki_refs.txt", "added": 0, "skipped": 0, "total": 0}
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during P4656 phase, skipping", flush=True)
        p4656_stats = {"output_file": "add_p4656_jawiki_refs.txt", "added": 0, "skipped": 0, "total": 0}
        rate_limited = True

    # Engishiki/Ritsuryō: Add Kokugakuin references to P13723 statements missing sources
    engishiki_ref_placeholder = {"output_file": ENGISHIKI_REFS_OUTPUT_FILE, "lines": 0, "total": 0, "remaining": 0, "completed": 0, "skipped_no_p13677": 0}
    try:
        engishiki_refs_stats = generate_engishiki_references() if not rate_limited else engishiki_ref_placeholder
    except (RateLimitError, requests.exceptions.HTTPError) as exc:
        print(f"WARNING: {exc.__class__.__name__} during Engishiki reference phase, skipping", flush=True)
        engishiki_refs_stats = engishiki_ref_placeholder
        rate_limited = True

    # Phase 3: Migrate old P31/P1552 values to P13723
    migration_stats = []
    for migration in MIGRATIONS:
        name = migration["name"]
        base = migration["output_file"].rsplit(".", 1)[0]
        add_file = f"{base}_add.txt"
        remove_file = f"{base}_remove.txt"
        placeholder = {
            "name": name, "description": migration["description"],
            "source_property": migration["source_property"],
            "determined_by": migration["determined_by"],
            "add_file": add_file, "remove_file": remove_file,
            "total": 0, "completed": 0, "remaining": 0, "add_lines": 0, "remove_lines": 0,
        }
        if rate_limited:
            migration_stats.append(placeholder)
            continue
        try:
            stats = generate_migration(migration)
            migration_stats.append(stats)
            time.sleep(2)  # Be nice to SPARQL endpoint between categories
        except (RateLimitError, requests.exceptions.HTTPError) as exc:
            print(f"WARNING: {exc.__class__.__name__} during {name} migration, skipping remaining migrations", flush=True)
            migration_stats.append(placeholder)
            rate_limited = True

    if rate_limited:
        print("\nWARNING: Some phases were skipped due to rate limiting. Partial results will be used.", flush=True)

    # Build site
    generate_html(p459_stats, migration_stats, prop_stats, hiteisha_stats, engishiki_refs_stats, shikinaisha_stats)
    generate_daily_operations(p459_stats, prop_stats, migration_stats, p4656_stats, hiteisha_stats, engishiki_refs_stats, shikinaisha_stats)

    # Copy all QuickStatements files into _site
    migration_files = []
    for m in migration_stats:
        migration_files.append(m["add_file"])
        migration_files.append(m["remove_file"])
        if m.get("underspec_file"):
            migration_files.append(m["underspec_file"])
    all_files = [
        p459_stats["output_file"], p4656_stats["output_file"],
        hiteisha_stats["output_file"], shikinaisha_stats["output_file"],
        engishiki_refs_stats["output_file"],
    ] + migration_files + [prop_stats["output_file"]]
    # Include P958 and P11250 files if they exist
    for extra_file in ["p958_qualifiers.txt", "p958_manual_review.txt", "p11250_miraheze_links.txt"]:
        if os.path.exists(extra_file):
            all_files.append(extra_file)
    for fname in all_files:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join("_site", fname))

    # Write summary JSON
    summary = {"p459": p459_stats, "p4656": p4656_stats, "hiteisha": hiteisha_stats, "shikinaisha": shikinaisha_stats, "engishiki_refs": engishiki_refs_stats, "migrations": migration_stats, "property_edits": prop_stats}
    with open("_site/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Done ===")
    print("Site built in _site/")


if __name__ == "__main__":
    main()
