#!/usr/bin/env python3
"""Script 2 of 2 — drop the two old Takano Shrine addresses, once the merge has landed.

REMOVE-ONLY. **Deliberately not registered in `ATOMIC_FILES`.** Run it by hand.

Emma 2026-07-10 decided that `Q11673131` (Takano Shrine, 津山市二宮) should carry one
address instead of two. Neither of the two it holds contains the other:

    〒708-0013 津山市二宮601      postcode + block number, no prefecture
    岡山県津山市二宮               prefecture, neither postcode nor block

So this is not a dedupe — dropping either loses something real. The merged form

    〒708-0013 岡山県津山市二宮601

is added by `generate_miscellaneous_edits.py`, which drips behind `conflict_gate`
with everything else. Only after that line has actually landed may the two old forms
go, and this script is the thing that checks.

**Why two scripts.** The daily batch runs its lines in random order. An add and a
remove in the same file could fire remove-first, and Takano Shrine would be left with
no address at all. So: script 1 only adds; script 2 only removes, and emits *nothing*
until a fresh SPARQL query sees the merged address live on the item. There is no
ordering to get wrong, because there is no ordering — the gate is the data itself.

    python generate_ronsha_address_merge_removals.py [--out FILE]

Exit 0 with an empty file means "the add has not landed yet". Run it again later.
"""
import argparse
import csv
import io
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "ronsha_address_merge_removals.txt"

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL = "https://query-main.wikidata.org/sparql"

P_ADDRESS = "P6375"

QID = "Q11673131"                                   # Takano Shrine, 津山市二宮
MERGED = "〒708-0013 岡山県津山市二宮601"              # added by script 1
SUPERSEDED = [                                      # removed here, after MERGED lands
    "〒708-0013 津山市二宮601",
    "岡山県津山市二宮",
]


def sparql_csv(query):
    r = requests.get(SPARQL, params={"query": query},
                     headers={"User-Agent": UA, "Accept": "text/csv"}, timeout=120)
    if r.status_code == 429:
        raise SystemExit("FATAL: 429 — bailing (429 policy)")
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def live_addresses(qid):
    rows = sparql_csv(
        'SELECT ?a WHERE {{ wd:{} wdt:{} ?a }}'.format(qid, P_ADDRESS))
    return {r["a"] for r in rows}


def removal_line(qid, address):
    return '-{}|{}|ja:"{}"'.format(qid, P_ADDRESS, address)


def needed_lines(live):
    """The removals that are safe *right now*, given what the item actually holds.

    Emits nothing unless the merged address is live: without it, removing the two old
    forms would leave the shrine with no address. Only removes what is still there.
    """
    if MERGED not in live:
        return [], "the merged address is not on the item yet — nothing to do"
    lines = [removal_line(QID, a) for a in SUPERSEDED if a in live]
    if not lines:
        return [], "the merge is complete; both old addresses are already gone"
    return lines, "merged address is live; {} old form(s) can go".format(len(lines))


def assert_remove_only(lines):
    bad = [l for l in lines if not l.lstrip().startswith("-")]
    if bad:
        raise RuntimeError("script 2 is REMOVE-ONLY: {!r}".format(bad[:3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lines, why = needed_lines(live_addresses(QID))
    assert_remove_only(lines)

    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")

    print(why)
    for l in lines:
        print("   " + l)
    print("\n{} line(s) -> {}".format(len(lines), path))
    if lines:
        print("\nNOT registered in ATOMIC_FILES. Submit by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
