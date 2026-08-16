"""
Generate QuickStatements to add P958 (section) qualifiers to P13677
(Kokugakuin University Digital Museum entry ID) on Ronsha items.

For each instance of Q135038714:
  - Look at P527 (has part) and P460 (said to be the same as) statements
  - If the statement has a P1352 (ranking) qualifier, note the number
  - Go to the linked item and find its P13677 statement
  - Generate a QuickStatement adding P958 = ranking number as qualifier

Disputed shikinaisha (P460 links without P1352 qualifiers) get
P958 = "n/a" (not applicable) on their Kokugakuin IDs.

Items with multiple P13677 statements are flagged for manual review.
Ranking numbers that don't follow expected patterns (sequential from 1,
occasional 0) are also flagged.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import io
import json
import sys
import requests
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}

OUTPUT_FILE = "p958_qualifiers.txt"
MANUAL_REVIEW_FILE = "p958_manual_review.txt"
SUMMARY_FILE = "p958_summary.json"

# Sequence-anomaly parents INVESTIGATED and cleared as INTENTIONAL (2026-07-11),
# each verified against the Kokugakuin entry page's 現社名など（１..N） ordering
# (docs/kokugakuin_ranking_anomaly_verdicts_2026-07.md). In every case the
# candidate ranks start at 2 because 現社名など（１） is the shrine's CURRENT SITE
# (現社地) — the parent/entry item itself — which is not stored as a self-
# referential P527 candidate. So the P527 candidates (former sites 旧社地, or a
# distinct 論社) are correctly ranked 2,3,… and the "expected 1" is a false alarm.
# This is an EXPLICIT per-item allowlist, not a loosened heuristic (Emma's rule).
SEQUENCE_ANOMALIES_CLEARED = {
    "Q11442961",   # 天王宮大歳神社 — (1)天王宮[self] (2)蒲神明宮
    "Q11659237",   # 雄神神社 — (1)雄神神社[self] (2)元雄神神社
    "Q135039294",  # 畠田神社 — (1)現社地[self] (2)(3)旧社地
    "Q135040569",  # 三重神社 — (1)現社地[self] (2)旧社地 (3)大屋神社
    "Q135041216",  # 百射山神社 — (1)[self] (2)元百射山神社
    "Q135041251",  # 和理比賣神社 — (1)[self] (2)(3)旧社地
}


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


def resolve_multi_p13677(p13677_values, parent_value):
    """Which of a child's several Kokugakuin IDs belongs to THIS parent?

    A 論社 candidate is listed under every parent entry it is a candidate for and
    carries one P13677 per parent entry, so the count is arity rather than ambiguity:
    the ID whose value equals the parent's own ID is the one this parent's ranking
    belongs to.

    Returns the single matching value, or None when it cannot be settled — no parent
    value, no match, or (defensively) more than one identical match. None means the
    item goes to a human, which is the safe direction: guessing would attach a section
    number to the wrong identifier.

    Verified against live Wikidata 2026-08-16 on Q98082987 (2 IDs / 2 parents),
    Q135186711 (2 / 2) and Q135190252 (3 / 3) — one unique match every time.
    """
    if not parent_value:
        return None
    matches = [v for v in p13677_values if v == parent_value]
    return matches[0] if len(matches) == 1 else None


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

        if non_zero != expected_non_zero and parent_qid not in SEQUENCE_ANOMALIES_CLEARED:
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
                # A candidate shrine carries ONE P13677 per parent entry it is listed
                # under, so the count is arity, not ambiguity: the child's ID whose value
                # equals THIS parent's ID is the one this parent's ranking belongs to.
                # Verified 2026-08-16 on Q98082987 (2 IDs / 2 parents), Q135186711 (2/2)
                # and Q135190252 (3 IDs / 3 parents) — one unique match every time.
                # Emma authorised applying it 2026-08-16.
                parent_val = parent_p13677.get(parent_qid)
                matched = resolve_multi_p13677(p13677_values, parent_val)
                if matched is not None:
                    quickstatements.append(
                        f'{child_qid}|P13677|"{matched}"|P958|"{ranking}"'
                    )
                    print(
                        f"  {child_qid} ({child['label']}) ← P958=\"{ranking}\" on "
                        f"P13677=\"{matched}\" [multi-ID, matched to parent {parent_qid}]"
                    )
                    continue
                # Anything that does NOT resolve to exactly one match still goes to a
                # human. That is the safety net, not a formality: with no parent value or
                # an ambiguous one there is no way to know which ID the ranking belongs to.
                manual_review.append(
                    f"{child_qid}\t{child['label']}\t"
                    f"parent={parent_qid} ({parent_data['label']})\t"
                    f"ranking={ranking}\t"
                    f"P13677_count={num_p13677}\t"
                    f"via {child['prop']}\t"
                    f"parent_id={parent_val or 'MISSING'}\tno unique match"
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

    # --- P958="n/a" for items with P13677 lacking P958 ---
    # Applies to every item with P13677 that does NOT already have a P958
    # qualifier AND is NOT typed as Q135038714 (Disputed Shikinaisha/Shikigeisha)
    # or Q135022904 (Shikinai Ronsha). Those two grouping types are excluded
    # because their children have real ranked sections (see block 1); we don't
    # want to overwrite their nuance with "n/a".
    # Items that already received a numeric P958 from block 1 above are also
    # skipped to avoid duplicate qualifiers on the same claim.
    disputed_query = """
    SELECT DISTINCT ?item ?itemLabel ?p13677 WHERE {
      ?item p:P13677 ?stmt .
      ?stmt ps:P13677 ?p13677 .
      FILTER NOT EXISTS { ?stmt pq:P958 ?anySection . }
      FILTER NOT EXISTS { ?item wdt:P31 wd:Q135038714 . }
      FILTER NOT EXISTS { ?item wdt:P31 wd:Q135022904 . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja" }
    }
    ORDER BY ?item
    """

    print("\n" + "=" * 60)
    print('Items with P13677 lacking P958 (excl. Q135038714/Q135022904) — P958="n/a"')
    print("=" * 60)

    print("\nQuerying SPARQL...")
    disputed_results = sparql_query(disputed_query)
    print(f"Found {len(disputed_results)} P13677 claims without P958.")

    # QIDs that already get a numeric P958 from block 1 — skip them
    already_ranked_qids = set()
    for line in quickstatements:
        already_ranked_qids.add(line.split("|", 1)[0])
    for line in new_p13677_statements:
        already_ranked_qids.add(line.split("|", 1)[0])

    disputed_statements = []
    disputed_skipped_existing = 0
    disputed_skipped_ranked = 0
    disputed_manual_review = []

    # Group by item so we can detect multiple-P13677 items
    item_claims = {}
    item_labels = {}
    for row in disputed_results:
        iqid = extract_qid(row["item"]["value"])
        ilabel = row.get("itemLabel", {}).get("value", iqid)
        p13677_value = row["p13677"]["value"]
        item_labels[iqid] = ilabel
        item_claims.setdefault(iqid, []).append(p13677_value)

    for iqid in sorted(item_claims.keys()):
        values = item_claims[iqid]
        label = item_labels[iqid]

        if iqid in already_ranked_qids:
            disputed_skipped_ranked += 1
            continue

        if len(values) > 1:
            disputed_manual_review.append(
                f"{iqid}\t{label}\t"
                f"ranking=not_applicable\t"
                f"P13677_count={len(values)}\t"
                f"multiple P13677 without P958"
            )
            continue

        p13677_value = values[0]
        disputed_statements.append(
            f'{iqid}|P13677|"{p13677_value}"|P958|"n/a"'
        )

    print(f"\nP958=\"n/a\" results:")
    print(f'  P958="n/a" statements generated: {len(disputed_statements)}')
    print(f"  Skipped (already ranked in block 1): {disputed_skipped_ranked}")
    print(f"  Flagged for manual review (multiple P13677): {len(disputed_manual_review)}")

    # Keep shim names for the summary/report code below
    disputed_skipped_no_p13677 = 0

    # Add to manual review
    manual_review.extend(disputed_manual_review)

    # Write QuickStatements output
    # Combine all types of statements
    all_statements = quickstatements + new_p13677_statements + disputed_statements

    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  P958 qualifiers for existing P13677: {len(quickstatements)}")
    print(f"  New P13677 + P958 (from parent): {added_from_parent}")
    print(f'  P958="n/a" (not Q135038714/Q135022904): {len(disputed_statements)}')
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
        "disputed_p958": len(disputed_statements),
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
