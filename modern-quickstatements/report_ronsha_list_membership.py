#!/usr/bin/env python3
"""The report Emma asked for in wiki-queue item (d), 2026-07-09.

REPORT ONLY. Emits nothing, removes nothing.

Her words, verbatim:

    "(d) part-of migration — on the actual shrine item, remove **every**
    part-of→Shikinaisha-list statement; add ONE derived from the list-entry item,
    taking the ordinal + follows/followed-by from the entry item's own
    (already-clean) statement. Two references: 'stated in' the Kokugakuin database +
    the entry id, and the jawiki Shikinaisha-list article. **Add-first /
    remove-later as two separate scripts.** BLOCKER to resolve first: when a Ronsha
    item carries several Kokugakuin entry ids (e.g. Q11677110 holds
    182062/182063/182065), which entry's ordinal becomes the single new statement?
    Build the report, then ask."

THE STRUCTURE, VERIFIED ON LIVE DATA
-----------------------------------
Emma 2026-07-10: *"the actual wikidata items for the list of the shrines contain the
entire list in them. They are very elaborate wikidata items, and to my knowledge, all
of their lists are deduplicated. This happened due to earlier import issues and they
were fixed in the list items but not the shrines themselves."*

    List of Shikinaisha in Shimotsuke Province
        has part -> Futaarayama Shrine   ordinal 4        <- the CLEAN, deduplicated list
        has part -> Murahino Shrine       ordinal 3
        …14 statements, 14 distinct targets, ZERO duplicates

    Futaarayama Shrine   (the ENTRY item)
        part of -> the list, ordinal 4, follows/followed by, Kokugakuin id 182030

    Futarasan Shrine     (the modern shrine, a Ronsha)
        part of -> the list, ordinal 4, with neighbours     }  four statements,
        part of -> the list, bare                           }  ALL of them junk
        part of -> two other things

The duplication came from piped links in the jawiki Shikinaisha list, where a shrine
that was part of another shrine got piped in. The list items were repaired; the shrine
items were not.

An entry item is therefore a "said to be the same as" target **that the list itself
names as a part**. Being said-to-be-the-same-as something is not sufficient: that is
how Q11677110 appeared to have three candidate ordinals when only two are real.

THE BLOCKER, MEASURED
---------------------
`Q11677110` Kashima Amatarashi Wake Shrine is said to be the same as two entry items,
**both genuine parts of the Mutsu list**, at ordinals 25 and 26. Its own five part-of
statements give 25, 26 and 28 — the 28 is junk. It is a candidate for two different
Engishiki entries, and no rule picks one.

This script classifies every Ronsha that has a list membership:

  UNAMBIGUOUS  exactly one entry item, in exactly one list -> fully determined.
  AMBIGUOUS    several entry items, or entries in several lists. Emma's blocker.
  NO-ENTRY     no "said to be the same as" target is a part of the list it claims.

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
P_HAS_PART = "P527"
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


def list_parts(list_claims):
    """{part_qid: ordinal} from a LIST item's own has-part statements.

    Emma 2026-07-10: *"the actual wikidata items for the list of the shrines contain
    the entire list in them … all of their lists are deduplicated. This happened due
    to earlier import issues and they were fixed in the list items but not the
    shrines themselves."*

    Verified: `List of Shikinaisha in Shimotsuke Province` has 14 has-part
    statements, 14 distinct targets, zero duplicates. Eleven carry an ordinal; the
    other three are class counts (Shikinaisha / Taisha / Shōsha) qualified by
    "quantity" instead. `Futaarayama Shrine`, the entry item, is a part.
    `Futarasan Shrine`, the modern shrine, is not.
    """
    out = {}
    for st in list_claims.get(P_HAS_PART, []):
        dv = st["mainsnak"].get("datavalue")
        if not dv:
            continue
        q = st.get("qualifiers", {})
        ords = [x["datavalue"]["value"] for x in q.get(P_ORDINAL, []) if "datavalue" in x]
        if not ords:
            continue                       # a class count, not a list entry
        out[dv["value"]["id"]] = ords[0]
    return out


def classify(shrine_claims, entry_ids, list_parts_by_list, lists):
    """(kind, {list: [(entry, ordinal), …]}) for one Ronsha.

    An entry item is a "said to be the same as" target that the LIST itself names as
    a part. Merely being said-to-be-the-same-as something is not enough — that is how
    Q11677110 appeared to have three candidate ordinals when only two are real.
    """
    claimed = {l for l, _o, _n in list_statements(shrine_claims, lists)}
    found = collections.defaultdict(list)
    for l in claimed:
        parts = list_parts_by_list.get(l, {})
        for e in entry_ids:
            if e in parts:
                found[l].append((e, parts[e]))

    if not found:
        return "no-entry", {}
    if len(found) == 1 and len(next(iter(found.values()))) == 1:
        return "unambiguous", dict(found)
    return "ambiguous", dict(found)


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
    list_ents = entities(lists)
    ents.update(list_ents)
    list_parts_by_list = {l: list_parts(list_ents[l].get("claims", {}))
                          for l in lists if l in list_ents}
    print("{} list entries across the {} lists".format(
        sum(len(v) for v in list_parts_by_list.values()), len(lists)))

    entry_ids = {e for q in shrines
                 for e in _values(ents[q].get("claims", {}), P_SAME_AS)}
    print("{} distinct 'said to be the same as' targets".format(len(entry_ids)))
    ents.update(entities(entry_ids - set(ents)))

    buckets = collections.Counter()
    detail = {"ambiguous": [], "no-entry": [], "unambiguous": []}
    for q in shrines:
        claims = ents[q].get("claims", {})
        kind, entry_statements = classify(
            claims, _values(claims, P_SAME_AS), list_parts_by_list, lists)
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
    for q, name, kids, nown, es in sorted(detail["ambiguous"], key=lambda r: -sum(len(v) for v in r[4].values())):
        ent_str = " · ".join(
            "{0}: ".format(label(ents.get(l, {"id": l}))) + ", ".join(
                "[{0}](https://www.wikidata.org/wiki/{0}) {1} @ {2}".format(
                    e, label(ents.get(e, {"id": e})), o)
                for e, o in sorted(pairs, key=lambda x: int(x[1])))
            for l, pairs in sorted(es.items()))
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
