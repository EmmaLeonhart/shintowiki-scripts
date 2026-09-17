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

⛔ Generates only. Nothing is delivered while `wikidata_editing_lockout.state` is shut.

Usage:
    python modern-quickstatements/generate_multi_ordinal_removals.py
    python modern-quickstatements/generate_multi_ordinal_removals.py --dry-run
"""
import argparse
import io
import json
import os
import sys

import wdqs_transport
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


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "multi_ordinal_removals.txt")

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
    """One WDQS query, through the shared transport.

    ⚠ The hand-rolled loop this replaces had the RIGHT backoff -- `for wait in
    (0, 15, 45, 135)`, the repo's own pattern -- and the right 429 bail. What it did
    not have was the retryable set: it caught `urllib.error.HTTPError` **only**, so a
    truncated body escaped the loop entirely and ended the run. That is the
    2026-09-13 incident this module was written for, in a file that reads as
    compliant at a glance. It also `continue`d on 503/504 alone, so a 500 or a 502
    was raised on the first attempt rather than retried.

    The throttle moves with it: it lived in this function rather than at the call
    sites so a caller could not forget it, which is the transport's own reason.
    """
    try:
        return wdqs_transport.query(query, timeout=180)
    except Exception as e:
        # Message kept from the hand-rolled version, but it now names the actual
        # failure. "kept timing out" was asserted unconditionally there, and would
        # have been printed for a malformed query just the same.
        print(f"WDQS failed ({type(e).__name__}: {e}). Wrote nothing.")
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

    # Sorted for the same reason as generate_orphan_membership_removals.py: SPARQL row
    # order is not stable, and unsorted output rewrote 48 of these 63 lines on the first
    # scheduled run with no statement actually changing.
    lines = sorted(set(lines))

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
