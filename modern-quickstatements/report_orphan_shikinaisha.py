#!/usr/bin/env python3
"""REPORT ONLY — the confirmed Shikinaisha that no Engishiki list names as a part.

Emits nothing. Touches nothing. Writes `docs/orphan_shikinaisha_2026-07.md`.

Emma 2026-07-10, on the list-membership work: *"there's confirmed shikinaisha i.e. not
disputed ones"* — the 126 Ronsha named as list parts were not the whole story, because
`Shikinaisha` (confirmed) is a different class from `Shikinai Ronsha` (disputed), and
2,863 items carry the confirmed one.

Of those, **2,713 are named as a part of an Engishiki list and 150 are not.** This
script asks what the 150 are.

THE ANSWER, in one line: they are overwhelmingly **modern shrine items carrying the
Shikinaisha class directly**, while the list names a *separate* entry item for the
same Engishiki record. The two items are duplicates of a kind — one is the shrine
standing today, the other is the 927 record.

The evidence for that reading is the Kokugakuin id. **2,700 of the 2,713 named entries
hold one — 99.5%.** Only 69 of the 150 do — 46%. An item the Kokugakuin 式内社 database
does not know is unlikely to be an Engishiki entry record.

An entry twin is found for a given orphan when any of these holds:

    same Kokugakuin id as a named entry            47
    same ja label as a named entry in its list     29
    same *normalised* ja label (旧字体 folded,       7
      之/ノ→の, ヶ/ケ→が, trailing 社/宮 dropped)

leaving 67 with no discoverable twin — 43 that claim a list, 20 that claim no list at
all, and 4 that hold their own Kokugakuin id yet are not named.

    python report_orphan_shikinaisha.py
"""
import collections
import csv
import io
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "docs", "orphan_shikinaisha_2026-07.md")

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL = "https://query-main.wikidata.org/sparql"

SHIKINAISHA = "Q134917286"      # confirmed
RONSHA = "Q135022904"           # disputed
JINMYOCHO = "Q11064932"

# 旧字体 → 新字体 for the characters that actually occur in these shrine names.
OLD_KANJI = str.maketrans("國會豐榮圓龍瀧藏彌澤淺齋", "国会豊栄円竜滝蔵弥沢浅斎")


def sparql_csv(query):
    r = urllib.request.Request(
        SPARQL + "?" + urllib.parse.urlencode({"query": query}),
        headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(r, timeout=300) as resp:
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))


def qid(u):
    return u.rsplit("/", 1)[-1] if u.startswith("http") else u


def normalise(name):
    """Fold the spelling variants that separate a modern shrine from its 927 record."""
    name = re.sub(r"\s*\([^)]*\)", "", name or "").translate(OLD_KANJI)
    name = name.replace("之", "の").replace("ノ", "の")
    name = name.replace("ヶ", "が").replace("ケ", "が")
    return re.sub(r"(神社|大社|神宮|社|宮)$", "", name)


def classify(q, claimed_lists, parts_of, ja_label, kokugakuin, dup_ids):
    """Why is this confirmed Shikinaisha not named as a part? Most specific first."""
    if q in dup_ids:
        return "twin: shares a Kokugakuin id with a named entry"
    twins = [e for l in claimed_lists for e in parts_of.get(l, ()) if e != q]
    mine = ja_label.get(q)
    if mine and any(ja_label.get(e) == mine for e in twins):
        return "twin: same ja label as a named entry in the list it claims"
    if mine and any(normalise(ja_label.get(e, "")) == normalise(mine) for e in twins):
        return "twin: same normalised ja label as a named entry in the list it claims"
    if not claimed_lists:
        return "no twin: claims no list at all"
    if q in kokugakuin:
        return "no twin: holds its own Kokugakuin id, yet no list names it"
    return "no twin: claims a list, has no Kokugakuin id"


def gather():
    parts_of = collections.defaultdict(set)
    for r in sparql_csv(
            "SELECT ?l ?e WHERE { ?l wdt:P361 wd:%s . ?l p:P527 ?s . "
            "?s ps:P527 ?e . ?s pq:P1545 ?o }" % JINMYOCHO):
        parts_of[qid(r["l"])].add(qid(r["e"]))
    parts = set().union(*parts_of.values()) if parts_of else set()

    confirmed = {qid(r["i"]) for r in sparql_csv(
        "SELECT ?i WHERE { ?i wdt:P31 wd:%s }" % SHIKINAISHA)}

    claims = collections.defaultdict(list)
    for r in sparql_csv(
            "SELECT ?i ?l WHERE { ?i wdt:P31 wd:%s . ?i wdt:P361 ?l . "
            "?l wdt:P361 wd:%s }" % (SHIKINAISHA, JINMYOCHO)):
        claims[qid(r["i"])].append(qid(r["l"]))

    kokugakuin = collections.defaultdict(list)
    for r in sparql_csv(
            "SELECT ?i ?k WHERE { ?i wdt:P31 wd:%s . ?i wdt:P13677 ?k }" % SHIKINAISHA):
        kokugakuin[qid(r["i"])].append(r["k"])

    ja_label = {qid(r["i"]): r["l"] for r in sparql_csv(
        "SELECT ?i ?l WHERE { ?i wdt:P31 wd:%s . ?i rdfs:label ?l "
        'FILTER(lang(?l)="ja") }' % SHIKINAISHA)}

    en_label = {qid(r["i"]): r["l"] for r in sparql_csv(
        "SELECT ?i ?l WHERE { ?i wdt:P31 wd:%s . ?i rdfs:label ?l "
        'FILTER(lang(?l)="en") }' % SHIKINAISHA)}

    list_label = {qid(r["l"]): r["n"] for r in sparql_csv(
        "SELECT ?l ?n WHERE { ?l wdt:P361 wd:%s . ?l rdfs:label ?n "
        'FILTER(lang(?n)="en") }' % JINMYOCHO)}

    ids_of_named = collections.defaultdict(list)
    for q, ks in kokugakuin.items():
        if q in parts:
            for k in ks:
                ids_of_named[k].append(q)
    dup_ids = {q for q in confirmed - parts
               if any(k in ids_of_named for k in kokugakuin.get(q, []))}

    return (parts, confirmed, claims, kokugakuin, ja_label, en_label,
            list_label, parts_of, dup_ids)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    (parts, confirmed, claims, kokugakuin, ja_label, en_label,
     list_label, parts_of, dup_ids) = gather()

    orphans = sorted(confirmed - parts)
    rows = []
    for q in orphans:
        rows.append((q, classify(q, claims.get(q, []), parts_of, ja_label,
                                 kokugakuin, dup_ids)))
    counts = collections.Counter(k for _q, k in rows)

    named = confirmed & parts
    with_id = sum(1 for q in named if q in kokugakuin)

    out = []
    out.append("# The confirmed Shikinaisha no Engishiki list names\n")
    out.append("**Report only.** Nothing emitted, nothing removed. "
               "Regenerate with `modern-quickstatements/report_orphan_shikinaisha.py`.\n")
    out.append("Emma 2026-07-10: *\"there's confirmed shikinaisha i.e. not disputed ones\"*.\n")
    out.append("| | |\n|---|---:|")
    out.append("| items with **instance of = Shikinaisha** (confirmed) | **%d** |" % len(confirmed))
    out.append("| …named as a part of an Engishiki list | **%d** |" % len(named))
    out.append("| …**not** named | **%d** |" % len(orphans))
    out.append("| of the named entries, how many hold a Kokugakuin entry id | **%d / %d** |"
               % (with_id, len(named)))
    out.append("| of the unnamed, how many hold one | **%d / %d** |"
               % (sum(1 for q in orphans if q in kokugakuin), len(orphans)))
    out.append("")
    out.append("Nearly every named entry holds a Kokugakuin id (%.1f%%); fewer than half the "
               "unnamed do (%.0f%%). An item the Kokugakuin 式内社 database does not know is "
               "unlikely to be an Engishiki entry record — it is more likely the shrine "
               "standing today. The %d named entries that lack an id are themselves worth a "
               "look; they are not covered by this report.\n"
               % (100.0 * with_id / len(named),
                  100.0 * sum(1 for q in orphans if q in kokugakuin) / len(orphans),
                  len(named) - with_id))

    out.append("## What the %d are\n" % len(orphans))
    out.append("| class | n |\n|---|---:|")
    for k, n in counts.most_common():
        out.append("| %s | %d |" % (k, n))
    twin = sum(n for k, n in counts.items() if k.startswith("twin"))
    out.append("")
    out.append("**%d of %d have a discoverable entry twin** already named by the list. "
               "For those, two items describe one Engishiki record: the modern shrine "
               "and the 927 entry. The remaining %d have no twin this script can find.\n"
               % (twin, len(orphans), len(orphans) - twin))

    for kind, _n in counts.most_common():
        out.append("## %s\n" % kind)
        out.append("| item | ja | en | claims |\n|---|---|---|---|")
        for q, k in rows:
            if k != kind:
                continue
            ls = ", ".join(list_label.get(l, l) for l in claims.get(q, [])) or "—"
            out.append("| [%s](https://www.wikidata.org/wiki/%s) | %s | %s | %s |"
                       % (q, q, ja_label.get(q, "—"), en_label.get(q, "—"), ls))
        out.append("")

    io.open(DOC, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for k, n in counts.most_common():
        print("%4d  %s" % (n, k))
    print("\n%d orphans -> %s" % (len(orphans), DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
