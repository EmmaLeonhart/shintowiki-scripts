"""
Generate QuickStatements to add P958 (section) qualifiers to P13677
(Kokugakuin University Digital Museum entry ID) on Ronsha items.

For each instance of Q135038714:
  - Look at P527 (has part) and P460 (said to be the same as) statements
  - If the statement has a P1352 (ranking) qualifier, note the number
  - Go to the linked item and find its P13677 statement
  - Generate a QuickStatement adding P958 = ranking number as qualifier

Items with multiple P13677 statements are flagged for manual review.
Ranking numbers that don't follow expected patterns (sequential from 1,
occasional 0) are also flagged.
"""

import io
import sys
import requests
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {
    "User-Agent": "ModernQuickstatements/1.0 (P958 qualifier bot)",
    "Accept": "application/sparql-results+json",
}

OUTPUT_FILE = "p958_qualifiers.txt"
MANUAL_REVIEW_FILE = "p958_manual_review.txt"


def sparql_query(query):
    """Run a SPARQL query and return results."""
    for attempt in range(3):
        try:
            resp = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["results"]["bindings"]
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429 and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  SPARQL rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def get_entities_batch(qids):
    """Fetch multiple entities in one API call (max 50)."""
    entities = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i+50]
        ids_str = "|".join(batch)
        for attempt in range(5):
            try:
                resp = requests.get(
                    WIKIDATA_API,
                    params={
                        "action": "wbgetentities",
                        "ids": ids_str,
                        "props": "claims",
                        "format": "json",
                    },
                    headers=HEADERS,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json().get("entities", {})
                entities.update(data)
                break
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429 and attempt < 4:
                    wait = 15 * (attempt + 1)
                    print(f"  API rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        # Pause between batches
        if i + 50 < len(qids):
            time.sleep(2)
    return entities


def extract_qid(uri):
    """Extract QID from a Wikidata entity URI."""
    return uri.rsplit("/", 1)[-1]


def analyze_p13677(entity):
    """Analyze P13677 claims on an entity.

    Returns (p13677_values, has_existing_p958, count).
    p13677_values is a list of the string values.
    """
    if not entity:
        return [], False, 0
    claims = entity.get("claims", {})
    p13677_claims = claims.get("P13677", [])
    has_p958 = False
    values = []
    for claim in p13677_claims:
        qualifiers = claim.get("qualifiers", {})
        if "P958" in qualifiers:
            has_p958 = True
        snak = claim.get("mainsnak", {})
        dv = snak.get("datavalue", {})
        if dv:
            values.append(dv.get("value", ""))
    return values, has_p958, len(p13677_claims)


def main():
    print("=" * 60)
    print("P958 Qualifier Generator for Kokugakuin Museum Entry IDs")
    print("=" * 60)

    # Query for all P527 and P460 links with P1352 qualifiers
    # on instances of Q135038714
    query = """
    SELECT ?parent ?parentLabel ?child ?childLabel ?ranking ?prop WHERE {
      ?parent wdt:P31 wd:Q135038714 .
      {
        ?parent p:P527 ?stmt .
        ?stmt ps:P527 ?child .
        ?stmt pq:P1352 ?ranking .
        BIND("P527" AS ?prop)
      } UNION {
        ?parent p:P460 ?stmt .
        ?stmt ps:P460 ?child .
        ?stmt pq:P1352 ?ranking .
        BIND("P460" AS ?prop)
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja" }
    }
    ORDER BY ?parent ?ranking
    """

    print("\nQuerying SPARQL for P527/P460 links with P1352 qualifiers...")
    results = sparql_query(query)
    print(f"Found {len(results)} links with ranking qualifiers.")

    if not results:
        print("No results found. Exiting.")
        return

    # Group by parent to validate ranking sequences
    parents = {}
    all_child_qids = set()
    for row in results:
        parent_qid = extract_qid(row["parent"]["value"])
        parent_label = row.get("parentLabel", {}).get("value", parent_qid)
        child_qid = extract_qid(row["child"]["value"])
        child_label = row.get("childLabel", {}).get("value", child_qid)
        ranking = int(float(row["ranking"]["value"]))
        prop = row["prop"]["value"]

        if parent_qid not in parents:
            parents[parent_qid] = {"label": parent_label, "children": []}
        parents[parent_qid]["children"].append({
            "qid": child_qid,
            "label": child_label,
            "ranking": ranking,
            "prop": prop,
        })
        all_child_qids.add(child_qid)

    print(f"Found {len(parents)} parent items with ranked children.")
    print(f"Unique child items to check: {len(all_child_qids)}")

    # Batch-fetch all child entities
    print(f"\nFetching entity data in batches of 50...")
    child_qid_list = sorted(all_child_qids)
    child_entities = get_entities_batch(child_qid_list)
    print(f"Fetched {len(child_entities)} entities.")

    # Process each parent and its children
    quickstatements = []
    manual_review = []
    skipped_existing = 0
    skipped_no_p13677 = 0
    flagged_sequence = []

    for parent_qid, parent_data in sorted(parents.items()):
        children = sorted(parent_data["children"], key=lambda c: c["ranking"])
        rankings = [c["ranking"] for c in children]

        # Check sequence: should be 1,2,3... or 0,1,2,3...
        if rankings and rankings[0] == 0:
            expected = list(range(0, len(rankings)))
        else:
            expected = list(range(1, len(rankings) + 1))

        if rankings != expected:
            flagged_sequence.append(
                f"  {parent_qid} ({parent_data['label']}): "
                f"rankings={rankings}, expected={expected}"
            )

        for child in children:
            child_qid = child["qid"]
            ranking = child["ranking"]

            entity = child_entities.get(child_qid)
            p13677_values, has_p958, num_p13677 = analyze_p13677(entity)

            if num_p13677 == 0:
                skipped_no_p13677 += 1
                continue

            if has_p958:
                skipped_existing += 1
                continue

            if num_p13677 > 1:
                manual_review.append(
                    f"{child_qid}\t{child['label']}\t"
                    f"parent={parent_qid} ({parent_data['label']})\t"
                    f"ranking={ranking}\t"
                    f"P13677_count={num_p13677}\t"
                    f"via {child['prop']}"
                )
                continue

            # Single P13677, no existing P958 — generate QuickStatement
            p13677_value = p13677_values[0]
            quickstatements.append(
                f'{child_qid}|P13677|"{p13677_value}"|P958|"{ranking}"'
            )
            print(
                f"  {child_qid} ({child['label']}) ← P958=\"{ranking}\" "
                f"[parent: {parent_qid}, via {child['prop']}]"
            )

    # Write QuickStatements output
    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  QuickStatements generated: {len(quickstatements)}")
    print(f"  Skipped (already has P958): {skipped_existing}")
    print(f"  Skipped (no P13677): {skipped_no_p13677}")
    print(f"  Flagged for manual review (multiple P13677): {len(manual_review)}")
    print(f"  Flagged sequence anomalies: {len(flagged_sequence)}")

    if quickstatements:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(quickstatements) + "\n")
        print(f"\nQuickStatements written to {OUTPUT_FILE}")

    if manual_review or flagged_sequence:
        with open(MANUAL_REVIEW_FILE, "w", encoding="utf-8") as f:
            if flagged_sequence:
                f.write("=== RANKING SEQUENCE ANOMALIES ===\n")
                f.write("These parents have non-sequential rankings:\n\n")
                f.write("\n".join(flagged_sequence) + "\n\n")

            if manual_review:
                f.write("=== MULTIPLE P13677 — NEEDS MANUAL REVIEW ===\n")
                f.write("These items have multiple P13677 statements.\n")
                f.write("Add the correct P958 qualifier manually.\n\n")
                f.write("QID\tLabel\tParent\tRanking\tP13677_count\tLink_type\n")
                f.write("\n".join(manual_review) + "\n")

        print(f"Manual review items written to {MANUAL_REVIEW_FILE}")


if __name__ == "__main__":
    main()
