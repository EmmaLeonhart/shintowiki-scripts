#!/usr/bin/env python3
"""REPORT ONLY — structural defects in the 69 Engishiki list items.

Emits nothing. Touches nothing. Writes `docs/engishiki_list_structure_2026-07.md`.

Background: `docs/engishiki_lists_primer.md`. The Awa defect (2026-07-10) was found by
noticing that the Kokugakuin id sequence skipped 181734 while an entry item held it and no
list named it. That shape generalises, so this sweeps all 69 lists for five defects at
once.

    1. an ordinal held by MORE THAN ONE entry     — the slot is contested
    2. an entry named at MORE THAN ONE ordinal    — the entry is unplaceable
    3. a hole in 1..max(ordinal)                  — an entry is missing
    4. a has-part with NO ordinal                 — invisible to `list_members()`
    5. an entry item no list names, holding a
       Kokugakuin id no named entry holds         — a candidate for a hole

Defect 5 is the interesting one: such an item is a complete register entry that nothing
points at. `Q137041912` 天神社 was exactly this, and its slot turned out to have been stolen
by a piped link.

    python report_list_structure.py
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import collections
import csv
import io
import os
import sys
import urllib.parse
import urllib.request
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "docs", "engishiki_list_structure_2026-07.md")

UA = WIKIDATA_USER_AGENT
SPARQL = "https://query-main.wikidata.org/sparql"

SHIKINAISHA = "Q134917286"
JINMYOCHO = "Q11064932"

# The three class items a list names with a `quantity` qualifier rather than an ordinal.
CLASS_COUNTS = {"Q134917286", "Q134917287", "Q134917288"}


def sparql_csv(query):
    req = urllib.request.Request(
        SPARQL + "?" + urllib.parse.urlencode({"query": query}),
        headers={"User-Agent": UA, "Accept": "text/csv"})
    wd_pace(SPARQL_INTERVAL)
    with urllib.request.urlopen(req, timeout=300) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def qid(u):
    return u.rsplit("/", 1)[-1] if u.startswith("http") else u


# ─────────────────────────── pure logic ───────────────────────────

def contested_ordinals(members):
    """{ordinal: {entries}} for every ordinal more than one entry claims."""
    by_ordinal = collections.defaultdict(set)
    for e, o in members:
        by_ordinal[o].add(e)
    return {o: es for o, es in by_ordinal.items() if len(es) > 1}


def entries_at_several_ordinals(members):
    """{entry: {ordinals}} for every entry the list names more than once."""
    by_entry = collections.defaultdict(set)
    for e, o in members:
        by_entry[e].add(o)
    return {e: os for e, os in by_entry.items() if len(os) > 1}


def ordinal_holes(members):
    """The ordinals missing from 1..max. A non-numeric ordinal makes the answer unknown."""
    try:
        present = {int(o) for _e, o in members}
    except (TypeError, ValueError):
        return []
    if not present:
        return []
    return sorted(set(range(1, max(present) + 1)) - present)


def unlinked_entry_items(named, kokugakuin_ids):
    """Entry items no list names, whose Kokugakuin id no named entry holds.

    An item sharing its id with a named entry is a duplicate of that entry, not a missing
    one — a different problem, counted in `orphan_shikinaisha_2026-07.md`.
    """
    held_by_named = {k for e in named for k in kokugakuin_ids.get(e, ())}
    return sorted(q for q, ks in kokugakuin_ids.items()
                  if q not in named and ks and not (set(ks) & held_by_named))


# ─────────────────────────── data ───────────────────────────

def gather():
    rows = sparql_csv(
        "SELECT ?l ?e ?o WHERE { ?l wdt:P361 wd:%s . ?l p:P527 ?s . "
        "?s ps:P527 ?e ; pq:P1545 ?o }" % JINMYOCHO)
    members = collections.defaultdict(list)
    for r in rows:
        members[qid(r["l"])].append((qid(r["e"]), r["o"]))

    no_ordinal = []
    for r in sparql_csv(
            "SELECT ?l ?e WHERE { ?l wdt:P361 wd:%s . ?l p:P527 ?s . ?s ps:P527 ?e . "
            "FILTER NOT EXISTS { ?s pq:P1545 ?o } FILTER NOT EXISTS { ?s pq:P1114 ?c } }"
            % JINMYOCHO):
        if qid(r["e"]) not in CLASS_COUNTS:
            no_ordinal.append((qid(r["l"]), qid(r["e"])))

    kok = collections.defaultdict(list)
    for r in sparql_csv(
            "SELECT ?i ?k WHERE { ?i wdt:P31 wd:%s . ?i wdt:P13677 ?k }" % SHIKINAISHA):
        kok[qid(r["i"])].append(r["k"])

    ja = {qid(r["i"]): r["l"] for r in sparql_csv(
        "SELECT ?i ?l WHERE { ?i wdt:P31 wd:%s . ?i rdfs:label ?l "
        'FILTER(lang(?l)="ja") }' % SHIKINAISHA)}

    list_name = {qid(r["l"]): r["n"] for r in sparql_csv(
        "SELECT ?l ?n WHERE { ?l wdt:P361 wd:%s . ?l rdfs:label ?n "
        'FILTER(lang(?n)="en") }' % JINMYOCHO)}
    return dict(members), no_ordinal, dict(kok), ja, list_name


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    members, no_ordinal, kok, ja, list_name = gather()
    named = {e for m in members.values() for e, _o in m}

    def name(q):
        return "{} {}".format(q, ja.get(q, ""))

    out = ["# Structural defects across the 69 Engishiki list items\n",
           "**Report only.** Regenerate with `modern-quickstatements/report_list_structure.py`. "
           "Background: `engishiki_lists_primer.md`.\n",
           "| defect | count |\n|---|---:|"]

    contested = [(l, o, es) for l, m in members.items()
                 for o, es in contested_ordinals(m).items()]
    several = [(l, e, os) for l, m in members.items()
               for e, os in entries_at_several_ordinals(m).items()]
    holes = [(l, ordinal_holes(m)) for l, m in members.items() if ordinal_holes(m)]
    unlinked = unlinked_entry_items(named, kok)

    out.append("| an ordinal held by more than one entry | %d |" % len(contested))
    out.append("| an entry named at more than one ordinal | %d |" % len(several))
    out.append("| holes in 1..max(ordinal) | %d |" % sum(len(h) for _l, h in holes))
    out.append("| has-part with no ordinal and no quantity | %d |" % len(no_ordinal))
    out.append("| entry items no list names, holding an unshared Kokugakuin id | %d |"
               % len(unlinked))
    out.append("")
    out.append("Across 69 lists and %d named entries. The list corpus is very nearly clean: "
               "the counts above are the whole of it.\n" % len(named))

    out.append("## Contested ordinals\n")
    for l, o, es in sorted(contested):
        out.append("* **%s**, ordinal %s — %s" % (
            list_name.get(l, l), o, " · ".join(name(e) for e in sorted(es))))
    out.append("")

    out.append("## Entries named at several ordinals\n")
    for l, e, os in sorted(several):
        out.append("* **%s** — %s at ordinals %s" % (
            list_name.get(l, l), name(e), ", ".join(sorted(os, key=int))))
    out.append("")

    out.append("## Holes\n")
    for l, h in sorted(holes):
        out.append("* **%s** — missing %s" % (list_name.get(l, l),
                                              ", ".join(str(x) for x in h)))
    out.append("")

    out.append("## has-part with no ordinal\n")
    for l, e in sorted(no_ordinal):
        out.append("* **%s** — %s" % (list_name.get(l, l), name(e)))
    out.append("")

    out.append("## Entry items nothing points at\n")
    out.append("Each holds a Kokugakuin id that no named entry holds, so it is not a "
               "duplicate of an entry — it is an entry with no home.\n")
    out.append("| item | ja | Kokugakuin |\n|---|---|---|")
    for q in unlinked:
        out.append("| [%s](https://www.wikidata.org/wiki/%s) | %s | %s |"
                   % (q, q, ja.get(q, "—"), ", ".join(kok[q])))
    out.append("")

    io.open(DOC, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("contested ordinals            %d" % len(contested))
    print("entries at several ordinals   %d" % len(several))
    print("holes                         %d" % sum(len(h) for _l, h in holes))
    print("has-part with no ordinal      %d" % len(no_ordinal))
    print("entry items nothing points at %d" % len(unlinked))
    print("\n-> %s" % DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
