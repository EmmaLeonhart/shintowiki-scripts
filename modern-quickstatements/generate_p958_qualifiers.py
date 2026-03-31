"""
Generate QuickStatements to add P958 (section) qualifiers to P13677
(Kokugakuin University Digital Museum entry ID) on Ronsha items.

For each instance of Q135038714:
  - Look at P527 (has part) and P460 (said to be the same as) statements
  - If the statement has a P1352 (ranking) qualifier, note the number
  - Go to the linked item and find its P13677 statement
  - Generate a QuickStatement adding P958 = ranking number as qualifier

Disputed shikinaisha (P460 links without P1352 qualifiers) get
P958 = Q105729336 (not applicable) on their Kokugakuin IDs.

Items with multiple P13677 statements are flagged for manual review.
Ranking numbers that don't follow expected patterns (sequential from 1,
occasional 0) are also flagged.
"""

import io
import json
import sys
import requests
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}

OUTPUT_FILE = "p958_qualifiers.txt"
MANUAL_REVIEW_FILE = "p958_manual_review.txt"
SUMMARY_FILE = "p958_summary.json"


class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests response is received."""


def sparql_query(query):
    """Run a SPARQL query with retry + exponential backoff on 429."""
    max_retries = 4
    for attempt in range(max_retries + 1):
        resp = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=60,
        )
        if resp.status_code == 429:
            if attempt < max_retries:
                wait = 30 * (2 ** attempt)
                print(f"429 Too Many Requests — retrying in {wait}s (attempt {attempt + 1}/{max_retries})", flush=True)
                time.sleep(wait)
                continue
            print(f"FATAL: 429 Too Many Requests after {max_retries} retries — bailing")
            raise RateLimitError(f"429 Too Many Requests: {resp.url}")
        resp.raise_for_status()
        return resp.json()["results"]["bindings"]


def get_entities_batch(qids):
    """Fetch multiple entities in one API call (max 50)."""
    entities = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i+50]
        ids_str = "|".join(batch)
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
        if resp.status_code == 429:
            print(f"FATAL: 429 Too Many Requests from Wikidata API — bailing to avoid further rate-limit violations")
            raise RateLimitError(f"429 Too Many Requests: {resp.url}")
        resp.raise_for_status()
        data = resp.json().get("entities", {})
        entities.update(data)
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

    # Batch-fetch parent entities to get their P13677 values
    parent_qid_list = sorted(parents.keys())
    print(f"\nFetching {len(parent_qid_list)} parent entities in batches of 50...")
    parent_entities = get_entities_batch(parent_qid_list)
    print(f"Fetched {len(parent_entities)} parent entities.")

    # Extract parent P13677 values
    parent_p13677 = {}
    for pqid, pentity in parent_entities.items():
        p13677_vals, _, count = analyze_p13677(pentity)
        if count == 1:
            parent_p13677[pqid] = p13677_vals[0]
        elif count > 1:
            print(f"  WARNING: parent {pqid} has {count} P13677 values — skipping as source")

    # Batch-fetch all child entities
    print(f"\nFetching {len(all_child_qids)} child entity data in batches of 50...")
    child_qid_list = sorted(all_child_qids)
    child_entities = get_entities_batch(child_qid_list)
    print(f"Fetched {len(child_entities)} entities.")

    # Process each parent and its children
    quickstatements = []
    new_p13677_statements = []
    manual_review = []
    skipped_existing = 0
    skipped_no_p13677 = 0
    added_from_parent = 0
    flagged_sequence = []

    for parent_qid, parent_data in sorted(parents.items()):
        children = sorted(parent_data["children"], key=lambda c: c["ranking"])
        rankings = [c["ranking"] for c in children]

        # Check sequence: zeroes mean "not in ordering" and multiple are allowed.
        # Non-zero rankings should form a contiguous 1,2,3... sequence.
        non_zero = [r for r in rankings if r != 0]
        expected_non_zero = list(range(1, len(non_zero) + 1))

        if non_zero != expected_non_zero:
            flagged_sequence.append({
                "qid": parent_qid,
                "label": parent_data["label"],
                "rankings": rankings,
                "expected": list(range(0, rankings.count(0))) + expected_non_zero,
            })

        for child in children:
            child_qid = child["qid"]
            ranking = child["ranking"]

            entity = child_entities.get(child_qid)
            p13677_values, has_p958, num_p13677 = analyze_p13677(entity)

            if num_p13677 == 0:
                # Try to add P13677 from parent's value
                if parent_qid in parent_p13677:
                    parent_val = parent_p13677[parent_qid]
                    new_p13677_statements.append(
                        f'{child_qid}|P13677|"{parent_val}"|P958|"{ranking}"'
                    )
                    added_from_parent += 1
                    print(
                        f"  {child_qid} ({child['label']}) ← NEW P13677=\"{parent_val}\" + P958=\"{ranking}\" "
                        f"[from parent: {parent_qid}, via {child['prop']}]"
                    )
                else:
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

    # --- Disputed shikinaisha: P460 links WITHOUT P1352 qualifiers ---
    # These are disputed identifications and get P958 = Q105729336 (not applicable)
    disputed_query = """
    SELECT ?parent ?parentLabel ?child ?childLabel WHERE {
      ?parent wdt:P31 wd:Q135038714 .
      ?parent p:P460 ?stmt .
      ?stmt ps:P460 ?child .
      FILTER NOT EXISTS {
        ?stmt pq:P1352 ?ranking .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja" }
    }
    ORDER BY ?parent ?child
    """

    print("\n" + "=" * 60)
    print("Disputed Shikinaisha — P460 without P1352 ranking")
    print("=" * 60)

    print("\nQuerying SPARQL for P460 links WITHOUT P1352 qualifiers...")
    disputed_results = sparql_query(disputed_query)
    print(f"Found {len(disputed_results)} disputed identification links.")

    disputed_statements = []
    disputed_new_p13677 = []
    disputed_skipped_existing = 0
    disputed_skipped_no_p13677 = 0
    disputed_manual_review = []

    if disputed_results:
        # Collect all disputed child QIDs
        disputed_children = {}
        for row in disputed_results:
            parent_qid_d = extract_qid(row["parent"]["value"])
            parent_label_d = row.get("parentLabel", {}).get("value", parent_qid_d)
            child_qid_d = extract_qid(row["child"]["value"])
            child_label_d = row.get("childLabel", {}).get("value", child_qid_d)
            disputed_children[child_qid_d] = {
                "label": child_label_d,
                "parent_qid": parent_qid_d,
                "parent_label": parent_label_d,
            }

        # Fetch entities for disputed children (skip any already fetched)
        new_disputed_qids = [q for q in disputed_children if q not in child_entities]
        if new_disputed_qids:
            print(f"Fetching {len(new_disputed_qids)} additional disputed child entities...")
            disputed_entities = get_entities_batch(new_disputed_qids)
            child_entities.update(disputed_entities)

        # Also need parent P13677 values for disputed children
        disputed_parent_qids = set(c["parent_qid"] for c in disputed_children.values())
        new_parent_qids = [q for q in disputed_parent_qids if q not in parent_p13677 and q not in parent_entities]
        if new_parent_qids:
            print(f"Fetching {len(new_parent_qids)} additional parent entities...")
            extra_parents = get_entities_batch(new_parent_qids)
            parent_entities.update(extra_parents)
            for pqid, pentity in extra_parents.items():
                p13677_vals, _, count = analyze_p13677(pentity)
                if count == 1:
                    parent_p13677[pqid] = p13677_vals[0]

        for child_qid_d, info in sorted(disputed_children.items()):
            entity = child_entities.get(child_qid_d)
            p13677_values, has_p958, num_p13677 = analyze_p13677(entity)

            if num_p13677 == 0:
                # Try to add P13677 from parent's value with P958=Q105729336
                if info["parent_qid"] in parent_p13677:
                    parent_val = parent_p13677[info["parent_qid"]]
                    disputed_new_p13677.append(
                        f'{child_qid_d}|P13677|"{parent_val}"|P958|Q105729336'
                    )
                    print(
                        f"  {child_qid_d} ({info['label']}) ← NEW P13677=\"{parent_val}\" + P958=Q105729336 (n/a) "
                        f"[disputed, from parent: {info['parent_qid']}]"
                    )
                else:
                    disputed_skipped_no_p13677 += 1
                continue

            if has_p958:
                disputed_skipped_existing += 1
                continue

            if num_p13677 > 1:
                disputed_manual_review.append(
                    f"{child_qid_d}\t{info['label']}\t"
                    f"parent={info['parent_qid']} ({info['parent_label']})\t"
                    f"ranking=disputed\t"
                    f"P13677_count={num_p13677}\t"
                    f"via P460 (no P1352)"
                )
                continue

            # Single P13677, no existing P958 — add Q105729336 (not applicable)
            p13677_value = p13677_values[0]
            disputed_statements.append(
                f'{child_qid_d}|P13677|"{p13677_value}"|P958|Q105729336'
            )
            print(
                f"  {child_qid_d} ({info['label']}) ← P958=Q105729336 (n/a) "
                f"[disputed, parent: {info['parent_qid']}]"
            )

    print(f"\nDisputed results:")
    print(f"  P958=Q105729336 for existing P13677: {len(disputed_statements)}")
    print(f"  New P13677 + P958=Q105729336 (from parent): {len(disputed_new_p13677)}")
    print(f"  Skipped (already has P958): {disputed_skipped_existing}")
    print(f"  Skipped (no P13677): {disputed_skipped_no_p13677}")
    print(f"  Flagged for manual review: {len(disputed_manual_review)}")

    # Add disputed items to manual review
    manual_review.extend(disputed_manual_review)

    # Write QuickStatements output
    # Combine all types of statements
    all_statements = quickstatements + new_p13677_statements + disputed_statements + disputed_new_p13677

    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  P958 qualifiers for existing P13677: {len(quickstatements)}")
    print(f"  New P13677 + P958 (from parent): {added_from_parent}")
    print(f"  Disputed P958=Q105729336: {len(disputed_statements) + len(disputed_new_p13677)}")
    print(f"  Total QuickStatements: {len(all_statements)}")
    print(f"  Skipped (already has P958): {skipped_existing + disputed_skipped_existing}")
    print(f"  Skipped (no P13677, parent also missing): {skipped_no_p13677 + disputed_skipped_no_p13677}")
    print(f"  Flagged for manual review (multiple P13677): {len(manual_review)}")
    print(f"  Flagged sequence anomalies: {len(flagged_sequence)}")

    if all_statements:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(all_statements) + "\n")
        print(f"\nQuickStatements written to {OUTPUT_FILE}")

    if manual_review or flagged_sequence:
        with open(MANUAL_REVIEW_FILE, "w", encoding="utf-8") as f:
            if flagged_sequence:
                f.write("=== RANKING SEQUENCE ANOMALIES ===\n")
                f.write("These parents have non-sequential rankings:\n\n")
                for a in flagged_sequence:
                    f.write(f"  {a['qid']} ({a['label']}): rankings={a['rankings']}, expected={a['expected']}\n")
                f.write("\n")

            if manual_review:
                f.write("=== MULTIPLE P13677 — NEEDS MANUAL REVIEW ===\n")
                f.write("These items have multiple P13677 statements.\n")
                f.write("Add the correct P958 qualifier manually.\n\n")
                f.write("QID\tLabel\tParent\tRanking\tP13677_count\tLink_type\n")
                f.write("\n".join(manual_review) + "\n")

        print(f"Manual review items written to {MANUAL_REVIEW_FILE}")

    # Write summary JSON for the page generator to pick up
    total_links = len(results)
    summary = {
        "total_links": total_links,
        "generated": len(all_statements),
        "p958_qualifiers": len(quickstatements),
        "new_p13677_from_parent": added_from_parent,
        "disputed_p958": len(disputed_statements) + len(disputed_new_p13677),
        "disputed_total": len(disputed_results),
        "completed": skipped_existing + disputed_skipped_existing,
        "skipped_no_p13677": skipped_no_p13677 + disputed_skipped_no_p13677,
        "manual_review": len(manual_review),
        "sequence_anomalies": len(flagged_sequence),
        "output_file": OUTPUT_FILE,
        "manual_review_file": MANUAL_REVIEW_FILE,
        "manual_review_items": manual_review,
        "sequence_anomaly_items": flagged_sequence,
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary written to {SUMMARY_FILE}")


if __name__ == "__main__":
    try:
        main()
    except RateLimitError:
        print("WARNING: Rate-limited, exiting with partial results (if any).", flush=True)
