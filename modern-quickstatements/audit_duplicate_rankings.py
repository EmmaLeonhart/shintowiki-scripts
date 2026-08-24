"""Is the same `shrine ranking` statement written twice on the same item?

Found on `Q135041321` while answering a question Emma asked about something else: it carries
`P13723 -> Q135009132` twice and `P13723 -> Q135160338` twice, each pair identical down to the
`P459` determination-method qualifier. The ritsuryo-funding migration touched ~4,800 items, so the
question is whether the add half double-wrote across the board or whether that one item is noise.

**Why this is measured before anything is staged.** A QuickStatements removal line is
VALUE-MATCHED: `-Q…|P13723|Q…` takes *every* statement with that value, not one of them. So the
obvious "delete the duplicate" line deletes both copies and leaves the item with nothing. That is
the same shape as the `P361` hazard, and it is why the 2026-07-10 audit exists.

**Why SPARQL here, when `CLAUDE.md` says not to hammer Wikidata.** The rule bans a *batched sweep* —
the failure it was written for fired ~365 queries in a run. This is ONE aggregate query whose
grouping happens server-side and whose result is only the duplicates. There is also no cheaper
source: this is a question about statement multiplicity on Wikidata itself, so a jawiki category
cannot answer it. Throttled at the repo floor, and it bails immediately on 429 per standing policy. Endpoint is
`query-main.wikidata.org`; the old `query.wikidata.org` is retired and pinned against by
`tests/test_sparql_endpoint_migration.py`, which caught this file on its first run.

READ-ONLY. Writes nothing to Wikidata; the lockout does not apply.

Usage:
    python modern-quickstatements/audit_duplicate_rankings.py
    python modern-quickstatements/audit_duplicate_rankings.py --json duplicate_rankings.json
"""
import argparse
import collections
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

ENDPOINT = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5

QUERY = """
SELECT ?item ?value ?method (COUNT(?st) AS ?n) WHERE {
  ?item p:P13723 ?st .
  ?st ps:P13723 ?value .
  OPTIONAL { ?st pq:P459 ?method . }
}
GROUP BY ?item ?value ?method
HAVING (COUNT(?st) > 1)
"""

TOTAL_QUERY = """
SELECT (COUNT(DISTINCT ?item) AS ?items) (COUNT(?st) AS ?statements) WHERE {
  ?item p:P13723 ?st .
}
"""


def run(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    time.sleep(WDQS_THROTTLE)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("HTTP 429 from WDQS — bailing immediately, per standing policy. Nothing measured.")
            sys.exit(1)
        raise


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    totals = run(TOTAL_QUERY)["results"]["bindings"][0]
    n_items = int(totals["items"]["value"])
    n_statements = int(totals["statements"]["value"])
    print("P13723 overall: %d statements across %d items" % (n_statements, n_items))

    rows = run(QUERY)["results"]["bindings"]
    print("duplicate (item, value, method) groups: %d" % len(rows))

    if not rows:
        print("\nNo duplication. Q135041321 would be the only case, and it is not one — "
              "re-read the item before concluding anything.")
        return

    per_item = collections.defaultdict(list)
    by_value = collections.Counter()
    extra_total = 0
    for r in rows:
        item = qid(r["item"]["value"])
        value = qid(r["value"]["value"])
        method = qid(r["method"]["value"]) if "method" in r else None
        count = int(r["n"]["value"])
        extra_total += count - 1
        per_item[item].append({"value": value, "method": method, "count": count})
        by_value[value] += 1

    print("affected items: %d" % len(per_item))
    print("redundant statements (copies beyond the first): %d" % extra_total)
    print("\nby ranking value:")
    for value, n in by_value.most_common(15):
        print("  %-16s %d groups" % (value, n))

    worst = sorted(per_item.items(), key=lambda kv: -sum(g["count"] for g in kv[1]))[:10]
    print("\nmost-duplicated items:")
    for item, groups in worst:
        detail = ", ".join("%s x%d%s" % (g["value"], g["count"],
                                         (" [P459=%s]" % g["method"]) if g["method"] else "")
                           for g in groups)
        print("  %-14s %s" % (item, detail))

    flagged = "Q135041321"
    print("\n%s: %s" % (flagged,
                        per_item.get(flagged, "NOT in the duplicate set — re-check the reading")))

    if args.json_out:
        path = args.json_out if os.path.isabs(args.json_out) else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), args.json_out)
        io.open(path, "w", encoding="utf-8").write(json.dumps({
            "p13723_statements": n_statements,
            "p13723_items": n_items,
            "duplicate_groups": len(rows),
            "affected_items": len(per_item),
            "redundant_statements": extra_total,
            "by_value": dict(by_value),
            "per_item": per_item,
        }, ensure_ascii=False, indent=2))
        print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
