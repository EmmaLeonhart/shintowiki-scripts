#!/usr/bin/env python3
"""Script 2 of 2 — strip the Engishiki list link from the Ronsha no list names.

REMOVE-ONLY. **Deliberately not registered in `ATOMIC_FILES`.** Run it by hand.

Emma 2026-07-10: *"Ronshas should not even have list membership."* And on the cause:
*"on the Shinto Shrine wiki on Japanese Wikipedia there was a large amount of pipe links
in the list where there was a shrine that was part of another shrine, ended up getting
piped in, resulting in massive duplications that have since been fixed."* The list items
were repaired; the shrine items were not.

The list is the source of truth. An item the list NAMES as a part (with a series ordinal)
is a member; `generate_list_membership_rebuild.py` — script 1 — gives it a clean statement.
An item the list does not name is not a member, whatever it claims, and this script takes
the claim away.

WHY THIS IS NOT REGISTERED
--------------------------
QuickStatements removes by **value**, not by statement id. `-Q1|P361|Qlist` deletes *a*
statement whose value is `Qlist`. If an item both kept a clean membership of `Qlist` and
carried junk pointing at `Qlist`, a value-matched removal could take the clean one. So the
removal must never fire on an item the list names.

Live state says that danger is not merely avoided but absent: of 2,277 Ronsha claiming a
list, **126 are named as a part and 2,151 are not, and no item is in both sets** — each
Ronsha claims exactly one list. The script still checks per (item, list) pair rather than
trusting that, because the safety property must hold at the moment it runs, not at the
moment it was written.

DUPLICATES
----------
94 pairs carry **more than one** `part of` statement to the same list — the original import
damage. One QuickStatements line removes one statement, so a pair with N statements gets N
identical lines. Re-running the generator against live state is therefore idempotent: as
lines land, the counts shrink.

    python generate_list_membership_removals.py [--out FILE]

Nothing is emitted for any item the list names. Nothing is emitted for a `part of` value
that is not an Engishiki list.
"""
import argparse
import collections
import csv
import io
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "list_membership_removals.txt"

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL = "https://query-main.wikidata.org/sparql"

RONSHA = "Q135022904"            # Shikinai Ronsha (disputed)
JINMYOCHO = "Q11064932"          # Engishiki Jinmyōchō
P_PART_OF = "P361"


def sparql_csv(query):
    req = urllib.request.Request(
        SPARQL + "?" + urllib.parse.urlencode({"query": query}),
        headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def qid(u):
    return u.rsplit("/", 1)[-1] if u.startswith("http") else u


def removal_line(item, list_qid):
    return "-{}|{}|{}".format(item, P_PART_OF, list_qid)


def removal_lines(claims, parts_of):
    """(lines, kept, dupes) for the Ronsha the lists do not name.

    `claims` is {(item, list): how many `part of` statements point that way}.
    `parts_of` is {list: {items the list names}}.

    A pair the list names is NEVER emitted: a value-matched removal there could take the
    clean statement script 1 built. A pair with N statements gets N lines, because one
    line removes one statement.
    """
    lines, kept, dupes = [], [], 0
    for (item, list_qid), n in sorted(claims.items()):
        if item in parts_of.get(list_qid, ()):
            kept.append((item, list_qid))
            continue
        if n > 1:
            dupes += 1
        lines.extend([removal_line(item, list_qid)] * n)
    return lines, kept, dupes


def assert_remove_only(lines):
    bad = [l for l in lines if not l.lstrip().startswith("-")]
    if bad:
        raise RuntimeError("script 2 is REMOVE-ONLY: {!r}".format(bad[:3]))


def assert_never_touches_a_named_part(lines, parts_of):
    """The one way this script could destroy data. Check it against the lines themselves."""
    bad = []
    for l in lines:
        item, _prop, list_qid = l[1:].split("|")
        if item in parts_of.get(list_qid, ()):
            bad.append(l)
    if bad:
        raise RuntimeError(
            "refusing to remove a membership the list NAMES: {!r}".format(bad[:3]))


def fetch():
    parts_of = collections.defaultdict(set)
    for r in sparql_csv(
            "SELECT ?l ?e WHERE { ?l wdt:P361 wd:%s . ?l p:P527 ?s . "
            "?s ps:P527 ?e . ?s pq:P1545 ?o }" % JINMYOCHO):
        parts_of[qid(r["l"])].add(qid(r["e"]))

    claims = collections.Counter()
    for r in sparql_csv(
            "SELECT ?i ?l WHERE { ?i wdt:P31 wd:%s . ?i p:P361 ?s . ?s ps:P361 ?l . "
            "?l wdt:P361 wd:%s }" % (RONSHA, JINMYOCHO)):
        claims[(qid(r["i"]), qid(r["l"]))] += 1
    return dict(claims), dict(parts_of)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    claims, parts_of = fetch()
    lines, kept, dupes = removal_lines(claims, parts_of)
    assert_remove_only(lines)
    assert_never_touches_a_named_part(lines, parts_of)

    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")

    items = {l[1:].split("|")[0] for l in lines}
    print("{} Ronsha->list claims".format(len(claims)))
    print("{} kept — the list names them as a part".format(len(kept)))
    print("{} removed, across {} items ({} of them carry duplicate statements)".format(
        len(lines), len(items), dupes))
    print("\n{} line(s) -> {}".format(len(lines), path))
    if lines:
        print("\nNOT registered in ATOMIC_FILES. Submit by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
