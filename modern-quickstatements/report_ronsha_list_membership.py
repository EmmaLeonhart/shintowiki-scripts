#!/usr/bin/env python3
"""The report Emma asked for in wiki-queue item (d), 2026-07-09.

REPORT ONLY. Emits nothing, removes nothing.

Her words, verbatim:

    "(d) P361 part-of migration (384 items) — on the actual shrine item, remove
    **every** P361→Shikinaisha-list statement; add ONE derived from the list-entry
    item, taking `P1545` ordinal + `P155`/`P156` from the entry item's own
    (already-clean) statement. Two references: `P248=Q135159299` + `P13677=<entry
    id>` … and the jawiki Shikinaisha-list article. **Add-first / remove-later as
    two separate scripts.** BLOCKER to resolve first: when a Ronsha item carries
    several `P13677` entry ids (e.g. Q11677110 holds 182062/182063/182065), which
    entry's ordinal becomes the single new statement? Build the report, then ask."

THE STRUCTURE, VERIFIED ON Futarasan
------------------------------------
`Q701927` Futarasan Shrine — a modern shrine, a Ronsha (candidate). It carries
**four** "part of" statements, two of them into the Shimotsuke list: one with
ordinal 4 and neighbours, one bare. All of them are the junk.

`Q95932360` Futaarayama Shrine — the **entry item** for Kokugakuin id 182030.
Exactly **one** "part of" statement: the Shimotsuke list, ordinal 4, with
`follows` and `followed by`. That is the clean source.

The shrine reaches its entry item through **"said to be the same as"**.

THE BLOCKER, MEASURED
---------------------
`Q11677110` Kashima Amatarashi Wake Shrine holds Kokugakuin ids 182062, 182063 and
182065, points at **two** entry items, and carries five "part of" statements into
one list with ordinals 25, 26 and 28. No rule picks one.

This script classifies every Ronsha that has a list membership:

  UNAMBIGUOUS  exactly one reachable entry item, and it has exactly one clean
               list statement -> the replacement statement is fully determined.
  AMBIGUOUS    several entry items, or several distinct ordinals among them.
               This is Emma's blocker set.
  NO-ENTRY     no reachable entry item at all -> nothing to copy from.

    python report_ronsha_list_membership.py [--out FILE]
"""
import argparse
import collections
import csv
import io
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(REPO, "docs", "ronsha_list_membership_2026-07.md")

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WD_API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query-main.wikidata.org/sparql"

RONSHA = "Q135022904"
JINMYOCHO = "Q11064932"
P_PART_OF = "P361"
P_ORDINAL = "P1545"
P_FOLLOWS = "P155"
P_FOLLOWED_BY = "P156"
P_SAME_AS = "P460"
P_KOKUGAKUIN = "P13677"


def sparql_csv(query):
    """CSV, not JSON: the JSON body for these result sets comes back truncated."""
    r = requests.get(SPARQL, params={"query": query},
                     headers={"User-Agent": UA, "Accept": "text/csv"}, timeout=300)
    if r.status_code == 429:
        raise SystemExit("FATAL: 429 — bailing (429 policy)")
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def entities(qids):
    out = {}
    qids = sorted(qids)
    for i in range(0, len(qids), 50):
        r = requests.get(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
            "props": "claims|labels", "languages": "en|ja", "format": "json"},
            headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
        time.sleep(0.3)
    return out


def _values(claims, prop):
    out = []
    for st in claims.get(prop, []):
        dv = st["mainsnak"].get("datavalue")
        if not dv:
            continue
        out.append(dv["value"]["id"] if dv["type"] == "wikibase-entityid" else dv["value"])
    return out


def list_statements(claims, lists):
    """[(list_qid, ordinal, n_neighbours)] for statements pointing at an Engishiki list."""
    out = []
    for st in claims.get(P_PART_OF, []):
        dv = st["mainsnak"].get("datavalue")
        if not dv or dv["value"]["id"] not in lists:
            continue
        q = st.get("qualifiers", {})
        ords = [x["datavalue"]["value"] for x in q.get(P_ORDINAL, []) if "datavalue" in x]
        nb = len(q.get(P_FOLLOWS, [])) + len(q.get(P_FOLLOWED_BY, []))
        out.append((dv["value"]["id"], ords[0] if ords else None, nb))
    return out


def label(ent):
    lab = ent.get("labels", {})
    return (lab.get("en") or lab.get("ja") or {}).get("value") or ent.get("id", "?")


def classify(shrine_claims, entry_ids, ents, lists):
    """(kind, detail) for one Ronsha."""
    entry_statements = {}
    for e in entry_ids:
        ent = ents.get(e)
        if not ent:
            continue
        sts = list_statements(ent.get("claims", {}), lists)
        if sts:
            entry_statements[e] = sts

    if not entry_statements:
        return "no-entry", {}

    ordinals = {(l, o) for sts in entry_statements.values() for l, o, _ in sts}
    if len(entry_statements) == 1 and len(ordinals) == 1:
        return "unambiguous", entry_statements
    return "ambiguous", entry_statements


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lists = {r["l"].rsplit("/", 1)[-1] for r in sparql_csv(
        "SELECT ?l WHERE { ?l wdt:%s wd:%s }" % (P_PART_OF, JINMYOCHO))}
    print("{} Engishiki lists".format(len(lists)))

    rows = sparql_csv("""
    SELECT DISTINCT ?item WHERE {
      ?item wdt:P31 wd:%s ; wdt:%s ?l .
      ?l wdt:%s wd:%s .
    }""" % (RONSHA, P_PART_OF, P_PART_OF, JINMYOCHO))
    shrines = sorted({r["item"].rsplit("/", 1)[-1] for r in rows})
    if args.limit:
        shrines = shrines[:args.limit]
    print("{} Ronsha carry a membership of an Engishiki list".format(len(shrines)))

    ents = entities(shrines)
    entry_ids = {e for q in shrines
                 for e in _values(ents[q].get("claims", {}), P_SAME_AS)}
    print("{} distinct 'said to be the same as' targets".format(len(entry_ids)))
    ents.update(entities(entry_ids - set(ents)))

    buckets = collections.Counter()
    detail = {"ambiguous": [], "no-entry": [], "unambiguous": []}
    for q in shrines:
        claims = ents[q].get("claims", {})
        kind, entry_statements = classify(
            claims, _values(claims, P_SAME_AS), ents, lists)
        buckets[kind] += 1
        detail[kind].append((q, label(ents[q]),
                             _values(claims, P_KOKUGAKUIN),
                             len(list_statements(claims, lists)),
                             entry_statements))

    write_report(args.out, buckets, detail, ents)
    for k in ("unambiguous", "ambiguous", "no-entry"):
        print("  {:12} {}".format(k, buckets[k]))
    print("-> {}".format(args.out))
    return 0


def write_report(path, buckets, detail, ents):
    total = sum(buckets.values())
    out = [
        "# Ronsha list membership — the report Emma asked for (wiki-queue item (d))",
        "",
        "**Report only.** Nothing emitted, nothing removed.",
        "",
        "## The plan, in Emma's words (2026-07-09)",
        "",
        "> on the actual shrine item, remove **every** part-of→Shikinaisha-list statement; add ONE",
        "> derived from the list-entry item, taking the ordinal + follows/followed-by from the entry",
        "> item's own (already-clean) statement. … **BLOCKER to resolve first:** when a Ronsha item",
        "> carries several Kokugakuin entry ids, which entry's ordinal becomes the single new",
        "> statement? Build the report, then ask.",
        "",
        "## The structure",
        "",
        "`Futarasan Shrine` (the modern shrine, a Ronsha) carries **four** part-of statements — two",
        "into the Shimotsuke list, one with ordinal 4 and neighbours and one bare. All junk.",
        "`Futaarayama Shrine`, its *entry item*, carries exactly **one**: the Shimotsuke list,",
        "ordinal 4, with follows and followed-by, and the Kokugakuin id 182030. The shrine reaches",
        "its entry item through **\"said to be the same as\"**.",
        "",
        "## Result",
        "",
        "| | |",
        "|---|---:|",
        "| Ronsha with a list membership | **{}** |".format(total),
        "| **unambiguous** — one entry item, one clean statement | **{}** |".format(buckets["unambiguous"]),
        "| **ambiguous** — several entry items or several ordinals | **{}** |".format(buckets["ambiguous"]),
        "| **no entry item reachable** | **{}** |".format(buckets["no-entry"]),
        "",
        "The unambiguous ones can be migrated without a decision. The ambiguous ones are Emma's",
        "blocker, listed in full below.",
        "",
        "## Ambiguous — which entry's ordinal wins?",
        "",
        "| Shrine | Kokugakuin ids | its own part-of statements | entry items and their ordinals |",
        "|---|---|---:|---|",
    ]
    for q, name, kids, nown, es in sorted(detail["ambiguous"], key=lambda r: -len(r[4])):
        ent_str = " · ".join(
            "[{0}](https://www.wikidata.org/wiki/{0}) {1} → {2}".format(
                e, label(ents.get(e, {"id": e})),
                ", ".join("ordinal {}".format(o or "—") for _l, o, _n in sts))
            for e, sts in sorted(es.items()))
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) {1} | {2} | {3} | {4} |".format(
            q, name, " ".join(kids) or "—", nown, ent_str))

    out += ["", "## No entry item reachable", "",
            "| Shrine | Kokugakuin ids | its own part-of statements |", "|---|---|---:|"]
    for q, name, kids, nown, _es in detail["no-entry"][:200]:
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) {1} | {2} | {3} |".format(
            q, name, " ".join(kids) or "—", nown))
    if len(detail["no-entry"]) > 200:
        out.append("| … | | {} more |".format(len(detail["no-entry"]) - 200))
    out.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))


if __name__ == "__main__":
    raise SystemExit(main())
