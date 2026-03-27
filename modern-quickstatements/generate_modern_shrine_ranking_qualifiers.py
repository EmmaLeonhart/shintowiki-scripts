"""
Generate QuickStatements for P13723 (shrine ranking) property work.

Phase 1: Add P459 (determination method or standard) → Q712534 qualifier to existing P13723 statements
Phase 2: Edit P13723 property definition (labels, constraints)
Phase 3: Migrate P31/P1552 shrine ranking values to P13723, preserving all
         existing qualifiers and references, and adding appropriate P459 qualifier.
"""

import io
import sys
import json
import os
import shutil
import time
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


def fetch_sparql(query, retries=3):
    """Run a SPARQL query against Wikidata, retrying on 429 rate-limit errors."""
    for attempt in range(retries):
        r = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=180,
        )
        if r.status_code == 429 and attempt < retries - 1:
            wait = 30 * (attempt + 1)
            print(f"  SPARQL 429 rate-limited, waiting {wait}s (attempt {attempt + 1}/{retries})...")
            time.sleep(wait)
            continue
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


P4656_OUTPUT_FILE = "p4656_jawiki_references.txt"


def generate_p4656_references():
    """Generate P4656 (Wikimedia import URL) references for modern shrine rankings.

    Only targets P13723 statements that already have P459=Q712534 (modern system)
    and have a Japanese Wikipedia sitelink, but no P4656 reference yet.
    """
    query = """
    SELECT ?item ?rankvalue ?articleName WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      ?stmt pq:P459 wd:Q712534 .
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
      ?stmt pq:P459 wd:Q712534 .
    }
    """

    print("\n=== P4656 Japanese Wikipedia references ===")
    print("Fetching total modern-qualified P13723 statements...")
    total = int(fetch_sparql(total_query)[0]["total"]["value"])
    print(f"Total P13723 statements with P459=Q712534: {total}")

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
        "description": "Add Wikimedia import URL (P4656) references pointing to ja.wikipedia for modern-qualified P13723 statements",
        "total": total,
        "remaining": remaining,
        "completed": total - remaining,
        "output_file": P4656_OUTPUT_FILE,
        "lines": len(lines),
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
    completed = total - remaining
    print(f"{source_prop} → P13723: {remaining} to migrate ({completed}/{total} done)")

    if not items_values:
        open(add_file, "w").close()
    else:
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
                    add_lines.extend(claim_to_qs_lines(item_id, claim, determined_by))

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

    return {
        "name": name,
        "description": migration["description"],
        "source_property": source_prop,
        "determined_by": determined_by,
        "total": total,
        "remaining": remaining,
        "completed": completed,
        "add_file": add_file,
        "remove_file": remove_file,
        "add_lines": len(add_lines) if items_values else 0,
        "remove_lines": len(remove_lines),
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


def generate_html(p459_stats, migration_stats, prop_stats, hiteisha_stats=None):
    """Generate the site index.html with progress for all categories."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def progress_pct(completed, total):
        return completed * 100 // total if total > 0 else 100

    p459_pct = progress_pct(p459_stats["completed"], p459_stats["total"])

    # Read first 200 lines for copy-paste boxes
    p459_batch = read_first_n_lines(p459_stats["output_file"])
    p459_batch_escaped = html_escape(p459_batch)
    prop_batch = read_first_n_lines(prop_stats["output_file"])
    prop_batch_escaped = html_escape(prop_batch)

    # P958 section from separate generator
    p958_summary = load_p958_summary()
    p958_section = generate_p958_html_section(p958_summary)

    # Shikinai Hiteisha removal section
    hiteisha_section = generate_hiteisha_html_section(hiteisha_stats) if hiteisha_stats else ""

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
  <p class="timestamp">Last updated: {generated}</p>

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
  <p>Add <code>P459</code> (determination method or standard) &rarr; <code>Q712534</code>
     (modern system of ranked Shinto shrines) to all existing <code>P13723</code> statements.</p>
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

  {hiteisha_section}

  {duplicates_section}

  <hr>
  <p class="timestamp">Generated automatically from SPARQL + Wikidata API data.</p>
</body>
</html>"""

    os.makedirs("_site", exist_ok=True)
    with open("_site/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_daily_operations(p459_stats, prop_stats, migration_stats, p4656_stats, hiteisha_stats=None):
    """Generate the daily operations page — a single combined box of what to run now.

    Priority order:
    - Phase 1 (P459 qualifiers) until complete
    - Phase 2 (property edits) after Phase 1 complete
    - P4656 references (always included when lines exist)
    - Phase 3 (migration adds + removes) after Phase 2 complete
    - P958 qualifiers always included
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

    # Always include Shikinai Hiteisha removals
    hiteisha_count = 0
    if hiteisha_stats and os.path.exists(hiteisha_stats["output_file"]):
        with open(hiteisha_stats["output_file"], "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
                    hiteisha_count += 1

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
    {"<em>Includes " + str(hiteisha_count) + " Shikinai Hiteisha removal lines</em>" if hiteisha_count else ""}
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
    # Phase 1: P459 qualifiers for existing P13723 statements
    p459_stats = generate_p459_qualifiers()

    # Phase 2: Property-level edits to P13723 (after modern qualifiers, before migrations)
    prop_stats = generate_property_edits()

    # Remove P31=Q135026601 (Shikinai Hiteisha) statements
    hiteisha_stats = generate_hiteisha_removals()

    # P4656: Add Japanese Wikipedia references to modern-qualified P13723 statements
    p4656_stats = generate_p4656_references()

    # Phase 3: Migrate old P31/P1552 values to P13723
    migration_stats = []
    for migration in MIGRATIONS:
        stats = generate_migration(migration)
        migration_stats.append(stats)
        time.sleep(2)  # Be nice to SPARQL endpoint between categories

    # Build site
    generate_html(p459_stats, migration_stats, prop_stats, hiteisha_stats)
    generate_daily_operations(p459_stats, prop_stats, migration_stats, p4656_stats, hiteisha_stats)

    # Copy all QuickStatements files into _site
    migration_files = []
    for m in migration_stats:
        migration_files.append(m["add_file"])
        migration_files.append(m["remove_file"])
    all_files = [p459_stats["output_file"], p4656_stats["output_file"], hiteisha_stats["output_file"]] + migration_files + [prop_stats["output_file"]]
    # Include P958 files if they exist
    for p958_file in ["p958_qualifiers.txt", "p958_manual_review.txt"]:
        if os.path.exists(p958_file):
            all_files.append(p958_file)
    for fname in all_files:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join("_site", fname))

    # Write summary JSON
    summary = {"p459": p459_stats, "p4656": p4656_stats, "hiteisha": hiteisha_stats, "migrations": migration_stats, "property_edits": prop_stats}
    with open("_site/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Done ===")
    print("Site built in _site/")


if __name__ == "__main__":
    main()
