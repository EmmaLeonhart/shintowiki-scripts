#!/usr/bin/env python3
"""Reference the `P31 = Q134917286` (Shikinaisha) statements to the Kokugakuin
University Shrine Database, the way their sibling statements already are.

Emma 2026-07-09:

    "All P31 Shikinaisha (Q134917286) items should get the Kokugakuin university
    citation thing just like others. This is to go into the edits queue thing."

"Just like others" is literal. On Q135039995, `P31 = Q135038714` and
`P31 = Q135160342` each carry a reference of `P248 = Q135159299` (Kokugakuin
University Shrine database) + `P13677 = <entry id>`, and its coordinate does too
— but `P31 = Q134917286` carries no reference at all. Across Wikidata, *every*
one of the 2,863 Shikinaisha statements is unreferenced.

ADD-ONLY, therefore drip-safe, therefore ATOMIC_FILES ("the edits queue thing").
`direct_daily_edits` finds the existing claim by value and calls `wbsetreference`
on it, so nothing creates a duplicate P31 statement.

SELF-HEALING. The query only returns statements with no reference at all, so a
statement already cited drops out of the next regeneration on its own.

WHAT IS SKIPPED, AND WHY
------------------------
The entry id in the reference has to be *this item's* Kokugakuin entry. An item
holding several `P13677` values cannot have one attributed to it by elimination
(that is the same trap as the P361 rebuild), and an item holding none has nothing
to cite. Both are skipped and counted rather than guessed at:

    2,760 emittable | 94 with no P13677 | 9 with several   (2026-07-09)

    python generate_shikinaisha_kokugakuin_refs.py [--out FILE]
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import io
import json
import os
import shutil
import sys
import time

import requests

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}

SHIKINAISHA = "Q134917286"     # the class whose P31 statement gets the citation
KOKUGAKUIN_DB = "Q135159299"   # P248 — Kokugakuin University Shrine database
OUTPUT_FILE = "shikinaisha_kokugakuin_refs.txt"

_last = 0.0


def sparql(query):
    global _last
    for attempt in range(5):
        gap = time.time() - _last
        if gap < 3:
            time.sleep(3 - gap)
        r = requests.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"},
                         headers=HEADERS, timeout=180)
        _last = time.time()
        if r.status_code == 429:
            raise SystemExit("FATAL: 429 Too Many Requests — bailing (429 policy)")
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        try:
            return json.loads(r.text, strict=False)["results"]["bindings"]
        except (ValueError, KeyError):
            print(f"  truncated body ({len(r.text)} bytes) — retrying", flush=True)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("SPARQL kept returning truncated bodies")


def build_query():
    """Unreferenced Shikinaisha P31 statements on items with exactly one entry id.

    The HAVING(=1) subquery is the attribution guard: a single P13677 is the only
    case where the entry id provably belongs to this item.
    """
    return f"""
    SELECT ?item ?eid WHERE {{
      {{
        SELECT ?item (SAMPLE(?e) AS ?eid) WHERE {{
          ?item wdt:P31 wd:{SHIKINAISHA} ; wdt:P13677 ?e .
        }} GROUP BY ?item HAVING(COUNT(DISTINCT ?e) = 1)
      }}
      ?item p:P31 ?st .
      ?st ps:P31 wd:{SHIKINAISHA} .
      FILTER NOT EXISTS {{ ?st prov:wasDerivedFrom ?ref }}
    }}
    """


def build_skip_query(having):
    return f"""
    SELECT (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      ?item p:P31 ?st . ?st ps:P31 wd:{SHIKINAISHA} .
      FILTER NOT EXISTS {{ ?st prov:wasDerivedFrom ?ref }}
      {having}
    }}
    """


def qs_reference(qid, eid):
    return f'{qid}|P31|{SHIKINAISHA}|S248|{KOKUGAKUIN_DB}|S13677|"{eid}"'


def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    # direct_daily_edits reads ATOMIC_FILES by BARE NAME from this directory and
    # silently `continue`s past a missing path, so a batch written only under
    # _site/ never reaches Wikidata. Write where the editor looks; copy to _site.
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Querying unreferenced Shikinaisha P31 statements...", flush=True)
    rows = sparql(build_query())

    lines, seen = [], set()
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        eid = r["eid"]["value"]
        if qid in seen:
            continue  # one reference per item, even if P31 is stated twice
        seen.add(qid)
        if '"' in eid or "|" in eid:
            print(f"  skipping unquotable entry id on {qid}: {eid!r}")
            continue
        lines.append(qs_reference(qid, eid))

    path = args.out
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    publish_to_site(path)

    no_id = sparql(build_skip_query(f"FILTER NOT EXISTS {{ ?item wdt:P13677 ?e }}"))
    many = sparql(build_skip_query(
        "{ SELECT ?item WHERE { ?item wdt:P13677 ?e } GROUP BY ?item HAVING(COUNT(DISTINCT ?e) > 1) }"
    ))
    print(f"\n  {len(lines)} references to add")
    print(f"  skipped, no P13677 to cite      : {no_id[0]['n']['value']}")
    print(f"  skipped, several P13677 (cannot attribute): {many[0]['n']['value']}")
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
