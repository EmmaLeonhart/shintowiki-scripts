"""
Generate QuickStatements for P13723 (shrine ranking) property work.

Phase 1: Add P459 (determination method or standard) → Q712534 qualifier to existing P13723 statements
Phase 2: Migrate P31/P1552 shrine ranking values to P13723, preserving all
         existing qualifiers and references, and adding appropriate P459 qualifier.
"""

import io
import sys
import json
import os
import shutil
import requests
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MAX_LINES_PER_BATCH = 200  # Budget ~200 QuickStatements per day per file

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {
    "User-Agent": "ModernQuickstatements/1.0 (shrine ranking migration)",
    "Accept": "application/sparql-results+json",
}

# Phase 0: Property-level edits to P13723 itself
# Broadens P13723 from "modern shrine ranking" to general "shrine ranking"
PROPERTY_EDITS_FILE = "edit_p13723_property.txt"
PROPERTY_EDITS = [
    'P13723|Len|"shrine ranking"',
    'P13723|Lfr|"classement des sanctuaires"',
    'P13723|Lid|"peringkat kuil Shinto"',
    'P13723|Lja|"神社の社格"',
    'P13723|Lnl|"schrijnrang"',
    'P13723|Ltok|"nanpa pi tomo sewi"',
    'P13723|Lca|"rang de santuaris"',
    'P13723|Lmk|"ранг на светилиште"',
    '-P13723|P1629|Q712534',
    'P13723|P1629|Q10444029',
    'P13723|P2302|Q21510856|P459',
]

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
    },
]


def fetch_sparql(query):
    """Run a SPARQL query against Wikidata."""
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=180,
    )
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


def claim_to_qs_lines(item_id, claim, determined_by):
    """Convert a Wikidata claim to QS v1 lines migrating it to P13723.

    The new P13723 statement gets:
    - The original value
    - P459 (determination method or standard) qualifier with the appropriate ranking system
    - All original qualifiers preserved
    - All original references preserved (flattened into one reference group per line)
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
    """Phase 1: Add P459 qualifiers to existing P13723 statements."""
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
    for r in results:
        item = qid(r["item"]["value"])
        rankvalue = qid(r["rankvalue"]["value"])
        all_lines.append(f"{item}|P13723|{rankvalue}|P459|Q712534")

    with open(output_file, "w", encoding="utf-8") as f:
        for line in all_lines:
            f.write(line + "\n")

    print(f"Written {len(all_lines)} lines to {output_file}")

    return {
        "name": "P459 qualifiers (determination method)",
        "description": "Add P459 (determination method or standard) → Q712534 (modern system of ranked Shinto shrines) to existing P13723 statements",
        "total": total,
        "remaining": remaining,
        "completed": completed,
        "output_file": output_file,
        "lines": len(all_lines),
    }


def rebuild_claim_with_p459(item_id, claim, p1027_value):
    """Rebuild a P13723 claim replacing P1027 with P459, preserving all other qualifiers and references.

    Returns QuickStatements lines for the new statement with:
    - The original value
    - P459 qualifier (replacing P1027) with the same value
    - All other original qualifiers preserved
    - All original references preserved
    """
    main_value = snak_to_qs(claim["mainsnak"])
    if not main_value:
        return []

    parts = [item_id, "P13723", main_value]

    # Add P459 replacing P1027, then all other qualifiers
    parts.extend(["P459", p1027_value])

    qualifiers = claim.get("qualifiers", {})
    qual_order = claim.get("qualifiers-order", list(qualifiers.keys()))
    for prop in qual_order:
        if prop == "P1027":
            continue  # Skip P1027 — replaced by P459 above
        for qsnak in qualifiers.get(prop, []):
            val = snak_to_qs(qsnak)
            if val is not None:
                parts.extend([prop, val])

    # Preserve references
    references = claim.get("references", [])

    if references:
        ref = references[0]
        ref_order = ref.get("snaks-order", list(ref.get("snaks", {}).keys()))
        for prop in ref_order:
            for rsnak in ref["snaks"].get(prop, []):
                val = snak_to_qs(rsnak)
                if val is not None:
                    parts.extend([f"S{prop[1:]}", val])

    lines = ["|".join(parts)]

    # Additional reference groups as separate lines
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


def generate_p1027_to_p459_replacement():
    """Phase 1.5: Replace existing P1027 qualifiers with P459 on P13723 statements.

    Finds all P13723 statements that still have a P1027 qualifier,
    generates QuickStatements to remove the old statement and re-add it with P459
    instead of P1027, preserving all other qualifiers and references.
    """
    query = """
    SELECT ?item ?rankvalue ?conferredBy WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      ?stmt pq:P1027 ?conferredBy .
    }
    ORDER BY ?item
    """

    print("\n=== Phase 1.5: Replace P1027 → P459 on existing P13723 ===")
    print("Fetching P13723 statements with P1027 qualifier...")
    results = fetch_sparql(query)
    print(f"Found {len(results)} statements to update")

    if not results:
        output_file = "replace_p1027_with_p459.txt"
        open(output_file, "w").close()
        return {
            "name": "Replace P1027 with P459",
            "description": "Replace P1027 (conferred by) qualifiers with P459 (determination method or standard) on existing P13723 statements",
            "total": 0,
            "remaining": 0,
            "completed": 0,
            "output_file": output_file,
            "lines": 0,
        }

    # Group by item to know which items to fetch
    items_p1027 = {}
    for r in results:
        item = qid(r["item"]["value"])
        rankvalue = qid(r["rankvalue"]["value"])
        conferred = qid(r["conferredBy"]["value"])
        items_p1027.setdefault(item, []).append((rankvalue, conferred))

    # Fetch full claim details from Wikidata API to get all qualifiers + references
    print(f"Fetching claim details ({len(items_p1027)} items)...")
    all_claims = fetch_claims_batch(list(items_p1027.keys()), "P13723")

    output_file = "replace_p1027_with_p459.txt"
    lines = []
    for item_id, targets in sorted(items_p1027.items()):
        for rankvalue, conferred in targets:
            # Find the matching claim in the API results
            for claim in all_claims.get(item_id, []):
                cv = snak_to_qs(claim["mainsnak"])
                if cv != rankvalue:
                    continue
                # Check this claim actually has P1027 with the expected value
                p1027_snaks = claim.get("qualifiers", {}).get("P1027", [])
                has_match = any(snak_to_qs(s) == conferred for s in p1027_snaks)
                if not has_match:
                    continue
                # Remove the old statement
                lines.append(f"-{item_id}|P13723|{rankvalue}")
                # Re-add with P459 replacing P1027, preserving everything else
                lines.extend(rebuild_claim_with_p459(item_id, claim, conferred))
                break

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {output_file}")

    return {
        "name": "Replace P1027 with P459",
        "description": "Replace P1027 (conferred by) qualifiers with P459 (determination method or standard) on existing P13723 statements, preserving all other qualifiers and references",
        "total": len(results),
        "remaining": len(results),
        "completed": 0,
        "output_file": output_file,
        "lines": len(lines),
    }


def generate_migration(migration):
    """Phase 2: Migrate P31/P1552 to P13723 with qualifiers and references."""
    name = migration["name"]
    source_prop = migration["source_property"]
    values = migration["values"]
    determined_by = migration["determined_by"]
    output_file = migration["output_file"]

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
    remaining_query = f"""
    SELECT ?item ?value WHERE {{
      VALUES ?value {{ {values_sparql} }}
      ?item p:{source_prop} ?stmt .
      ?stmt ps:{source_prop} ?value .
      FILTER NOT EXISTS {{
        ?item p:P13723 ?s2 .
        ?s2 ps:P13723 ?value .
      }}
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
    completed = total - remaining
    print(f"{source_prop} → P13723: {remaining} to migrate ({completed}/{total} done)")

    if not items_values:
        open(output_file, "w").close()
        return {
            "name": name,
            "description": migration["description"],
            "source_property": source_prop,
            "determined_by": determined_by,
            "total": total,
            "remaining": 0,
            "completed": total,
            "output_file": output_file,
            "lines": 0,
        }

    # Fetch full claim details from Wikidata API to get qualifiers + references
    print(f"Fetching claim details ({len(items_values)} items)...")
    all_claims = fetch_claims_batch(list(items_values.keys()), source_prop)

    # For P31 migrations, check which items already have P31=Q845945 (Shinto shrine)
    # so we can add it before removing the old P31 value
    items_have_shinto_shrine = set()
    if source_prop == "P31":
        for item_id, claims in all_claims.items():
            for claim in claims:
                cv = snak_to_qs(claim["mainsnak"])
                if cv == "Q845945":
                    items_have_shinto_shrine.add(item_id)

    # Generate QuickStatements lines
    # For P31 migrations: add P31=Q845945 if missing, then add P13723, then remove old P31
    lines = []
    items_given_shinto_shrine = set()  # Track so we only add it once per item
    for item_id, target_values in sorted(items_values.items()):
        for claim in all_claims.get(item_id, []):
            cv = snak_to_qs(claim["mainsnak"])
            if cv in target_values:
                # If this is a P31 migration and item lacks P31=Q845945, add it first
                if source_prop == "P31" and item_id not in items_have_shinto_shrine and item_id not in items_given_shinto_shrine:
                    lines.append(f"{item_id}|P31|Q845945")
                    items_given_shinto_shrine.add(item_id)
                # Add the new P13723 statement with qualifiers/references
                lines.extend(claim_to_qs_lines(item_id, claim, determined_by))
                # Remove the old source property statement
                lines.append(f"-{item_id}|{source_prop}|{cv}")

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Written {len(lines)} lines to {output_file}")

    return {
        "name": name,
        "description": migration["description"],
        "source_property": source_prop,
        "determined_by": determined_by,
        "total": total,
        "remaining": remaining,
        "completed": completed,
        "output_file": output_file,
        "lines": len(lines),
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

    # Build sequence anomaly list
    anomaly_list = ""
    if summary.get("sequence_anomaly_items"):
        items = "\n".join(f"<li><code>{html_escape(a.strip())}</code></li>" for a in summary["sequence_anomaly_items"])
        anomaly_list = f"""
    <details>
      <summary><strong>{summary["sequence_anomalies"]} ranking sequence anomalies</strong></summary>
      <ul style="font-size: 0.85rem;">{items}</ul>
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


def generate_html(p459_stats, replace_stats, migration_stats, prop_stats):
    """Generate the site index.html with progress for all categories."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def progress_pct(completed, total):
        return completed * 100 // total if total > 0 else 100

    p459_pct = progress_pct(p459_stats["completed"], p459_stats["total"])

    # Phase 1 three-segment bar: green (P459 done), red (has P1027 wrong qualifier), gray (nothing)
    p459_total = p459_stats["total"] if p459_stats["total"] > 0 else 1
    p459_green_pct = p459_stats["completed"] * 100 / p459_total
    p459_red_count = replace_stats["total"]
    p459_red_pct = p459_red_count * 100 / p459_total

    # Read first 200 lines for copy-paste boxes
    p459_batch = read_first_n_lines(p459_stats["output_file"])
    p459_batch_escaped = html_escape(p459_batch)
    replace_batch = read_first_n_lines(replace_stats["output_file"])
    replace_batch_escaped = html_escape(replace_batch)
    prop_batch = read_first_n_lines(prop_stats["output_file"])
    prop_batch_escaped = html_escape(prop_batch)

    # P958 section from separate generator
    p958_summary = load_p958_summary()
    p958_section = generate_p958_html_section(p958_summary)

    # Duplicate properties section
    duplicates_section = generate_duplicates_section()

    migration_sections = ""
    for m in migration_stats:
        pct = progress_pct(m["completed"], m["total"])
        batch_lines = read_first_n_lines(m["output_file"])
        batch_escaped = html_escape(batch_lines)
        total_lines = m.get("lines", m["remaining"])
        shown = min(total_lines, MAX_LINES_PER_BATCH)
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
      <p>Today's batch: {shown} of {total_lines} total lines
         &mdash; <a href="{m["output_file"]}">Download all</a></p>
      <textarea class="qs-box" rows="10" readonly onclick="this.select()">{batch_escaped}</textarea>
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
    .progress-fill.red {{ background: #e53935; }}
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
  <p class="timestamp">Last updated: {generated}</p>

  <div class="instructions">
    <strong>How to use:</strong> Click a text box below to select its contents, then paste into
    <a href="https://quickstatements.toolforge.org/#/batch">QuickStatements</a>.
    Each box shows up to {MAX_LINES_PER_BATCH} lines (~1 day's budget). Full files available via download links.
    Run in order: Phase 1.5 first (fix existing P1027), then Phase 1 (add P459), then Phase 2, then each migration.
  </div>

  <h2>Phase 1: Add P459 qualifiers to existing P13723</h2>
  <p>Add <code>P459</code> (determination method or standard) &rarr; <code>Q712534</code>
     (modern system of ranked Shinto shrines) to all existing <code>P13723</code> statements.</p>
  <div class="stats">
    <strong>{p459_stats["completed"]} / {p459_stats["total"]} done</strong> ({p459_pct}%)
    &mdash; <span style="color:#e53935"><strong>{p459_red_count} with wrong qualifier (P1027)</strong></span>
    &mdash; <strong>{p459_stats["remaining"] - p459_red_count} with no qualifier</strong>
    <div class="progress-bar">
      <div class="progress-fill" style="width: {max(p459_green_pct, 2 if p459_stats['completed'] else 0):.1f}%">{p459_stats["completed"]}</div>
      <div class="progress-fill red" style="width: {max(p459_red_pct, 2 if p459_red_count else 0):.1f}%">{p459_red_count}</div>
    </div>
  </div>
  <p>Today's batch: {min(p459_stats.get("lines", p459_stats["remaining"]), MAX_LINES_PER_BATCH)} of {p459_stats.get("lines", p459_stats["remaining"])} total lines
     &mdash; <a href="{p459_stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{p459_batch_escaped}</textarea>

  <h2>Phase 1.5: Replace P1027 qualifiers with P459</h2>
  <p>Replace existing <code>P1027</code> (conferred by) qualifiers with <code>P459</code>
     (determination method or standard) on <code>P13723</code> statements that already have P1027.</p>
  <p>{replace_stats["total"]} statements to update ({replace_stats["lines"]} lines)
     &mdash; <a href="{replace_stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="10" readonly onclick="this.select()">{replace_batch_escaped}</textarea>

  <h2>Phase 2: Edit P13723 property definition</h2>
  <p>Broaden <code>P13723</code> from &ldquo;modern shrine ranking&rdquo; to general &ldquo;shrine ranking&rdquo;.
     Updates labels, changes subject type constraint from <code>Q712534</code> to <code>Q10444029</code>,
     and adds <code>P459</code> qualifier constraint.</p>
  <p>{prop_stats["lines"]} lines &mdash; <a href="{prop_stats["output_file"]}">Download all</a></p>
  <textarea class="qs-box" rows="6" readonly onclick="this.select()">{prop_batch_escaped}</textarea>

  <h2>Phase 3: Migrate old properties to P13723</h2>
  <p>Migrate <code>P31</code> / <code>P1552</code> shrine ranking values to <code>P13723</code>,
     preserving all existing qualifiers and references, and adding the appropriate
     <code>P459</code> (determination method or standard) qualifier.</p>
  {migration_sections}

  {p958_section}

  {duplicates_section}

  <hr>
  <p class="timestamp">Generated automatically from SPARQL + Wikidata API data.</p>
</body>
</html>"""

    os.makedirs("_site", exist_ok=True)
    with open("_site/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    # Phase 1: P459 qualifiers for existing P13723 statements
    p459_stats = generate_p459_qualifiers()

    # Phase 1.5: Replace existing P1027 qualifiers with P459
    replace_stats = generate_p1027_to_p459_replacement()

    # Phase 2: Property-level edits to P13723 (after modern qualifiers, before migrations)
    prop_stats = generate_property_edits()

    # Phase 3: Migrate old P31/P1552 values to P13723
    migration_stats = []
    for migration in MIGRATIONS:
        stats = generate_migration(migration)
        migration_stats.append(stats)
        time.sleep(2)  # Be nice to SPARQL endpoint between categories

    # Build site
    generate_html(p459_stats, replace_stats, migration_stats, prop_stats)

    # Copy all QuickStatements files into _site
    all_files = [p459_stats["output_file"], replace_stats["output_file"]] + [m["output_file"] for m in migration_stats] + [prop_stats["output_file"]]
    # Include P958 files if they exist
    for p958_file in ["p958_qualifiers.txt", "p958_manual_review.txt"]:
        if os.path.exists(p958_file):
            all_files.append(p958_file)
    for fname in all_files:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join("_site", fname))

    # Write summary JSON
    summary = {"p459": p459_stats, "replace_p1027": replace_stats, "migrations": migration_stats, "property_edits": prop_stats}
    with open("_site/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Done ===")
    print("Site built in _site/")


if __name__ == "__main__":
    main()
