"""Remove `part of` statements that carry more than one series ordinal.

Emma, 2026-08-25, on what a corrected statement should look like: *"I already established this ages
ago: we remove them entirely and then later on we have quickstatements that add proper membership
stuff for the lists."* So this does the removal half only. Rebuilding correct per-ordinal membership
is a separate, later job and is deliberately not attempted here.

**What the defect is.** A `part of` statement means one position in one list. A statement carrying
five `P1545` values at once — with five `P155` and five `P156` piled in beside them — is the
piped-link import collapse made literal: several register entries that pointed at the same shrine
were folded into a single statement. `Q110915859` 御笏神社 and `Q482065` are the worst, at five
ordinals each.

**Why splitting was rejected.** One statement per ordinal sounds tidy, but the `P155`/`P156`
qualifiers are piled in alongside and pairing five ordinals to five predecessors is not mechanical —
it would be a guess wearing the shape of a repair. Removal loses nothing that is not recoverable
from the list's own `P527` sequence.

**A value-matched removal takes EVERY statement on that item with that value, and that is the
point.** Emma, 2026-08-25: *"every single membership thing on those items should be removed unless
the membership of the Shikinaisha list is 100% accurate and is 100% what we want. We remove it and
then we add it again. This is very, very established."*

So an item carrying a collapsed statement has all of its `part of` into that list removed, not just
the collapsed one. An item whose membership was folded together once is not trusted to have got the
rest right, and re-adding correct membership is the later half of the job. An earlier draft of this
script skipped such items to protect the "good" statements beside the bad one — that was the wrong
instinct and is why this note is here.

⛔ Generates only. Nothing is delivered before the Wikidata lockout lifts on 2026-09-18.

Usage:
    python modern-quickstatements/generate_multi_ordinal_removals.py
    python modern-quickstatements/generate_multi_ordinal_removals.py --dry-run
"""
import argparse
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

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "multi_ordinal_removals.txt")
ENDPOINT = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5
_LAST = 0.0

# Every (item, list) pair, with how many statements join them and how many
# distinct ordinals those statements carry between them.
QUERY = """
SELECT ?item ?ja ?list (COUNT(DISTINCT ?st) AS ?stmts) (COUNT(DISTINCT ?ord) AS ?ords) WHERE {
  ?item wdt:P31 wd:Q845945 ; p:P361 ?st .
  ?st ps:P361 ?list .
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
  OPTIONAL { ?st pq:P1545 ?ord }
}
GROUP BY ?item ?ja ?list
"""


def sparql(query):
    """Throttle lives here, not at the call sites — a caller cannot forget it."""
    global _LAST
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    gap = time.monotonic() - _LAST
    if gap < WDQS_THROTTLE:
        time.sleep(WDQS_THROTTLE - gap)
    _LAST = time.monotonic()
    for wait in (0, 15, 45, 135):
        if wait:
            print("  backing off %ds" % wait, flush=True)
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("429 from WDQS — bailing, per standing policy.")
                sys.exit(1)
            if exc.code in (503, 504):
                print("  HTTP %d from WDQS" % exc.code)
                continue
            raise
    print("WDQS kept timing out; wrote nothing.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = sparql(QUERY)
    lines, skipped = [], []
    for b in rows:
        ords = int(b["ords"]["value"])
        if ords < 2:
            continue
        item = b["item"]["value"].rsplit("/", 1)[-1]
        lst = b["list"]["value"].rsplit("/", 1)[-1]
        ja = b.get("ja", {}).get("value", "")
        n = int(b["stmts"]["value"])
        lines.append("-%s|P361|%s" % (item, lst))
        if n > 1:
            # recorded, not skipped: the removal takes all n, which is intended
            skipped.append((item, ja, lst, ords, n))

    print("item/list pairs with a collapsed statement: %d" % len(lines))
    print("  of those, the removal also takes sibling statements: %d" % len(skipped))
    for item, ja, lst, ords, n in skipped:
        print("     %-14s %-18s -> %-14s %d ordinals, %d statements all removed"
              % (item, ja[:17], lst, ords, n))

    if args.dry_run:
        for ln in lines:
            print("   " + ln)
        return
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        if lines:
            fh.write("\n".join(lines) + "\n")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
