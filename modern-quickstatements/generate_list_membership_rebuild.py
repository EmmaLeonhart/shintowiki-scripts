#!/usr/bin/env python3
"""Script 1 of 2 — rebuild each Engishiki list entry's own "part of" statement.

ADD-ONLY. `assert_add_only()` refuses a `-` line from any code path. The paired
removal script is separate and unregistered, per the add-first/remove-later rule.

THE ALGORITHM (Emma, 2026-07-09 and 2026-07-10)
----------------------------------------------
    "on the actual shrine item, remove every part-of→Shikinaisha-list statement; add
    ONE derived from the list-entry item, taking the ordinal + follows/followed-by
    from the entry item's own (already-clean) statement."

    "the actual wikidata items for the list of the shrines contain the entire list in
    them … all of their lists are deduplicated. This happened due to earlier import
    issues and they were fixed in the list items but not the shrines themselves."

    "Ronshas should not even have list membership."
    "the part of a list thing is true and those 126 should be continued in the listing"

So the **list item** is the source of truth. It names its members with `has part`
statements carrying a `series ordinal`. Those targets — 2,839 of them — are the
entries. An item the list does not name is not a member, whatever it claims.

    an item the list NAMES as a part  -> keeps ONE clean "part of" statement
    an item the list does NOT name     -> loses its list link entirely (script 2)

Of 2,323 Shikinai Ronsha, only **126** are named as parts. The other ~2,151 carry the
junk, which came from piped links in the jawiki list where a shrine that was part of
another shrine got piped in. The list items were repaired; the shrine items were not.

WHAT THIS SCRIPT EMITS
----------------------
For every item the list names, on its `part of` → list statement:

    series ordinal      the list's own ordinal
    follows             the entry at the previous ordinal, if any
    followed by         the entry at the next ordinal, if any
    reference 1         stated in = Kokugakuin University Shrine database (Q135159299)
                        + Kokugakuin University Digital Museum entry ID
    reference 2         Wikimedia import URL = the jawiki list article

Neighbours are derived from the **list's own ordering**, not copied — that is what
makes the list the single source of truth.

Everything is diffed against live state: a statement that already has its ordinal,
its neighbours and both references produces no line, so the batch shrinks as it lands.

Output: `list_membership_rebuild.txt`, registered in `ATOMIC_FILES`.

    python generate_list_membership_rebuild.py [--out FILE] [--limit N]
"""
import argparse
import collections
import csv
import io
import os
import shutil
import sys
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "list_membership_rebuild.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WD_API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query-main.wikidata.org/sparql"

JINMYOCHO = "Q11064932"
KOKUGAKUIN_DB = "Q135159299"     # Kokugakuin University Shrine database

P_PART_OF = "P361"
P_HAS_PART = "P527"
P_ORDINAL = "P1545"              # series ordinal (string)
P_FOLLOWS = "P155"
P_FOLLOWED_BY = "P156"
P_STATED_IN = "P248"
P_KOKUGAKUIN = "P13677"          # entry ID (external-id)
P_IMPORT_URL = "P4656"


def sparql_csv(query):
    """CSV, not JSON: the JSON body for these result sets comes back truncated."""
    r = requests.get(SPARQL, params={"query": query},
                     headers={"User-Agent": UA, "Accept": "text/csv"}, timeout=300)
    if r.status_code == 429:
        raise SystemExit("FATAL: 429 — bailing (429 policy)")
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def entities(qids, props="claims"):
    out, qids = {}, sorted(qids)
    for i in range(0, len(qids), 50):
        r = requests.get(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
            "props": props, "format": "json"},
            headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
        time.sleep(0.3)
    return out


# ─────────────────────────── pure logic ───────────────────────────

def list_members(list_claims):
    """[(entry_qid, ordinal)] from a list item's has-part statements, ordinal-sorted.

    A has-part statement with no ordinal is a class count (Shikinaisha / Taisha /
    Shōsha, qualified by "quantity"), not a list entry.
    """
    out = []
    for st in list_claims.get(P_HAS_PART, []):
        dv = st["mainsnak"].get("datavalue")
        if not dv:
            continue
        ords = [x["datavalue"]["value"]
                for x in st.get("qualifiers", {}).get(P_ORDINAL, []) if "datavalue" in x]
        if not ords:
            continue
        out.append((dv["value"]["id"], ords[0]))
    return sorted(out, key=lambda p: _ordinal_key(p[1]))


def _ordinal_key(o):
    try:
        return (0, int(o))
    except (TypeError, ValueError):
        return (1, str(o))


def ambiguous_entries(members):
    """Entries the list names at MORE THAN ONE ordinal. Never emit a line for these.

    Two exist live (2026-07-10): the Izumo list names `Q135040786` at 28 and 29, and the
    Awa list names `Q11361262` at 3 and 5. Both are the original piped-link import damage,
    surviving on the list side. Without this guard the generator emits one head line per
    ordinal — two contradictory `series ordinal` values, both landing on the *same*
    statement (QuickStatements matches a statement by its value), and both carrying the
    neighbours of whichever position `neighbours()` happened to record last.

    Which ordinal is right cannot be decided from the list: the list is what is wrong.
    """
    ordinals = collections.defaultdict(set)
    for e, o in members:
        ordinals[e].add(o)
    return {e for e, os in ordinals.items() if len(os) > 1}


def contested_entries(members):
    """Entries sharing an ordinal with a DIFFERENT entry. Never emit a line for these.

    One live case (2026-07-10): the Izumo list puts both `Q135040786` 同社坐韓国伊大弖神社
    and `Q135040787` 筑陽神社 at ordinal 29. The register says 29 is 筑陽神社; the 韓国伊大弖
    entry belongs only at 28, where it also sits. So one of the two is wrong, and reading
    the list cannot say which — a position holding two entries is not a position.

    The Awa list has the mirror case: ordinal 3 will hold both `Q11361262`, which stole the
    slot, and `Q137041912` 天神社, which the register actually names there, until the bad
    statement is removed by hand.
    """
    by_ordinal = collections.defaultdict(set)
    for e, o in members:
        by_ordinal[o].add(e)
    return {e for es in by_ordinal.values() if len(es) > 1 for e in es}


def unemittable_entries(members):
    """Every entry this list cannot place: named at two ordinals, or sharing one."""
    return ambiguous_entries(members) | contested_entries(members)


def neighbours(members):
    """{entry: (previous_entry, next_entry)} from the list's own ordering.

    An entry the list names twice gets the neighbours of its LAST position. That is only
    safe because `unemittable_entries()` excludes such entries from emission entirely.
    """
    out = {}
    for i, (e, _o) in enumerate(members):
        prev = members[i - 1][0] if i > 0 else None
        nxt = members[i + 1][0] if i + 1 < len(members) else None
        out[e] = (prev, nxt)
    return out


def _statement_for(entry_claims, list_qid):
    for st in entry_claims.get(P_PART_OF, []):
        dv = st["mainsnak"].get("datavalue")
        if dv and dv["value"]["id"] == list_qid:
            return st
    return None


def _qualifier_values(st, prop):
    return [x["datavalue"]["value"] for x in st.get("qualifiers", {}).get(prop, [])
            if "datavalue" in x]


def _has_reference_with(st, prop):
    for ref in st.get("references", []):
        if prop in ref.get("snaks", {}):
            return True
    return False


def needed_lines(entry, list_qid, ordinal, prev, nxt, kokugakuin_id, list_url,
                 entry_claims):
    """The lines this entry still needs. Empty when it is already correct."""
    st = _statement_for(entry_claims, list_qid)

    have_ordinal = bool(st) and ordinal in _qualifier_values(st, P_ORDINAL)
    have_prev = (prev is None) or (bool(st) and any(
        v["id"] == prev for v in _qualifier_values(st, P_FOLLOWS)))
    have_next = (nxt is None) or (bool(st) and any(
        v["id"] == nxt for v in _qualifier_values(st, P_FOLLOWED_BY)))
    have_kokugakuin_ref = bool(st) and _has_reference_with(st, P_STATED_IN)
    have_url_ref = bool(st) and _has_reference_with(st, P_IMPORT_URL)

    # When the entry carries several Kokugakuin ids we never emit that reference,
    # so we must not wait for it — otherwise the head line is re-emitted for ever.
    kokugakuin_settled = have_kokugakuin_ref or not kokugakuin_id

    lines = []
    if not (have_ordinal and have_prev and have_next and kokugakuin_settled):
        head = "{}|{}|{}|{}|\"{}\"".format(entry, P_PART_OF, list_qid, P_ORDINAL, ordinal)
        if prev:
            head += "|{}|{}".format(P_FOLLOWS, prev)
        if nxt:
            head += "|{}|{}".format(P_FOLLOWED_BY, nxt)
        if kokugakuin_id:
            head += "|S{}|{}|S{}|\"{}\"".format(
                P_STATED_IN[1:], KOKUGAKUIN_DB, P_KOKUGAKUIN[1:], kokugakuin_id)
        lines.append(head)
    if not have_url_ref and list_url:
        lines.append("{}|{}|{}|S{}|\"{}\"".format(
            entry, P_PART_OF, list_qid, P_IMPORT_URL[1:], list_url))
    return lines


def assert_add_only(lines):
    bad = [l for l in lines if l.lstrip().startswith("-")]
    if bad:
        raise RuntimeError("script 1 is ADD-ONLY: {!r}".format(bad[:3]))


def publish_to_site(path):
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


# ─────────────────────────── main ───────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lists = sorted({r["l"].rsplit("/", 1)[-1] for r in sparql_csv(
        "SELECT ?l WHERE { ?l wdt:%s wd:%s }" % (P_PART_OF, JINMYOCHO))})
    if args.limit:
        lists = lists[:args.limit]
    print("{} Engishiki lists".format(len(lists)))

    list_ents = entities(lists, props="claims|sitelinks")
    members_by_list = {l: list_members(list_ents[l].get("claims", {})) for l in lists}
    total = sum(len(v) for v in members_by_list.values())
    print("{} list entries".format(total))

    entry_ids = {e for m in members_by_list.values() for e, _o in m}
    entry_ents = entities(entry_ids)
    print("{} entry items fetched".format(len(entry_ents)))

    lines, skipped_multi_kid, already = [], 0, 0
    unplaceable = []
    for l in lists:
        members = members_by_list[l]
        nb = neighbours(members)
        ambig = unemittable_entries(members)
        unplaceable.extend((l, e) for e in sorted(ambig))
        sl = (list_ents[l].get("sitelinks") or {}).get("jawiki", {}).get("title")
        list_url = ("https://ja.wikipedia.org/wiki/" +
                    urllib.parse.quote(sl.replace(" ", "_"))) if sl else None
        for e, ordinal in members:
            if e in ambig:
                continue
            ent = entry_ents.get(e)
            if not ent:
                continue
            claims = ent.get("claims", {})
            kids = [s["mainsnak"]["datavalue"]["value"]
                    for s in claims.get(P_KOKUGAKUIN, []) if s["mainsnak"].get("datavalue")]
            kid = kids[0] if len(kids) == 1 else None
            if len(kids) > 1:
                skipped_multi_kid += 1
            prev, nxt = nb[e]
            new = needed_lines(e, l, ordinal, prev, nxt, kid, list_url, claims)
            if not new:
                already += 1
            lines.extend(new)

    lines = sorted(set(lines))
    assert_add_only(lines)
    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")
    publish_to_site(path)

    print("\n{} entries already complete".format(already))
    print("{} entries carry several Kokugakuin ids (no database reference emitted)".format(
        skipped_multi_kid))
    print("{} entries the list cannot place — NOTHING emitted for them:".format(
        len(unplaceable)))
    for l, e in unplaceable:
        print("    {} in {}".format(e, l))
    print("{} lines -> {}".format(len(lines), path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
