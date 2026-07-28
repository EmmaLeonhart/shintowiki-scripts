#!/usr/bin/env python3
"""
audit_model_adoption.py
=======================
Measure how far Emma's shrine/temple data-modelling conventions have become the
norm on Wikidata. Emma 2026-07-28: *"a review of the degree that my data
modelling changes have become the norm for shrines and temples on wikidata."*

Three questions per convention, kept separate because they answer different
things:

  COVERAGE     — of the class population, how many items carry the statement at
                 all. ("Did the import land?")
  CONFORMANCE  — of the statements that exist, how many carry the full modelled
                 shape (the required qualifier / reference). ("Is the model
                 followed where the property is used?")
  REACH        — how much of the property's or role's use ACROSS ALL OF WIKIDATA
                 is this model. A convention that is 100% conformant inside the
                 shrine population but 2% of the property's global use is a
                 local house style; one that dominates the property globally has
                 become the norm for the property itself.

Attribution (`--attribution`) samples items and reads the Wikidata revision
comments — MediaWiki's auto-comments name the property (`[[Property:P825]]`) —
to see WHO introduced the statement. That separates "the model is followed" from
"the model is followed because we are the only editor doing it".

READ-ONLY: SPARQL + the read API only. Safe under a Wikidata edit freeze. 429
bails immediately, no retries (repo policy).

    python audit_model_adoption.py                       # conformance survey
    python audit_model_adoption.py --attribution         # + who-added sampling
    python audit_model_adoption.py --json out.json       # machine-readable
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
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WDQS = "https://query-main.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"

SHRINE = "Q845945"       # Shinto shrine
TEMPLE = "Q5393308"      # Buddhist temple (Japan)


def wdqs(query, timeout=180):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": USER_AGENT, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit("429 from WDQS — bailing (repo policy: no retries).")
        return None                      # 500 = query timeout; report it, don't die
    except Exception:
        return None


def count(query):
    """Run a single-row SELECT of one COUNT; return the int, or None on timeout.

    Every metric is its own COUNT(DISTINCT …) query rather than one query with
    OPTIONAL joins. OPTIONAL multiplies rows — a statement with two references
    is counted twice — which silently inflated the first draft of this audit
    (P13723 read 19,939 statements against a true 16,995). One count per query
    is slower and right.
    """
    rows = wdqs(query)
    if rows is None:
        return None
    if not rows:
        return 0
    return int(next(iter(rows[0].values()))["value"])


# ─────────────────────────────────────────────────────────────────────────────
# The checks: (key, title, {metric: single-COUNT query}). One count per query —
# see count() for why. The model is docs/wikidata_shrine_festival_model.md plus
# the individual generate_*.py docstrings; the QIDs below come from there.
# ─────────────────────────────────────────────────────────────────────────────
ENGISHIKI_LIST = "Q11064932"      # 延喜式神名帳 — the per-province lists are P361 of it
RONSHA = "Q135022904"             # Shikinai Ronsha

CHECKS = [
    ("population", "Class populations", {
        "shrines": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} }}",
        "temples": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} }}",
    }),

    # 1. Reisai — P837 + P3831=Q11385469 role (+ P793 festival qualifier).
    ("reisai", "Reisai: P837 + P3831=Q11385469", {
        "shrine_items": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P837 ?v }}",
        "shrine_stmts": f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st }}",
        "conforming": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st .
                          ?st pq:P3831 wd:Q11385469 }}""",
        "missing_role": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st .
                            FILTER NOT EXISTS {{ ?st pq:P3831 wd:Q11385469 }} }}""",
        "with_p793": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st .
                         ?st pq:P793 ?e }}""",
        "referenced": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st .
                          ?st prov:wasDerivedFrom ?r }}""",
        "global_stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P837 ?st }",
        "global_any_role": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P837 ?st . ?st pq:P3831 ?r }",
        "global_reisai_role": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P837 ?st . ?st pq:P3831 wd:Q11385469 }",
    }),

    # 2. Bunrei — P612 + P1013=Q195793 in the same statement, never bare.
    ("bunrei", "Bunrei: P612 + P1013=Q195793", {
        "shrine_items": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P612 ?v }}",
        "shrine_stmts": f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P612 ?st }}",
        "conforming": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P612 ?st .
                          ?st pq:P1013 wd:Q195793 }}""",
        "bare": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P612 ?st .
                    FILTER NOT EXISTS {{ ?st pq:P1013 wd:Q195793 }} }}""",
        "global_stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P612 ?st }",
        "global_any_p1013": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P612 ?st . ?st pq:P1013 ?c }",
        "global_bunrei": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P612 ?st . ?st pq:P1013 wd:Q195793 }",
    }),

    # 3. Shintai — P825 + P3831=Q327532. Zero uses existed before this model.
    ("shintai", "Shintai: P825 + P3831=Q327532", {
        "stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P825 ?st . ?st pq:P3831 wd:Q327532 }",
        "on_shrines": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?x wdt:P31 wd:{SHRINE} ; p:P825 ?st .
                          ?st pq:P3831 wd:Q327532 }}""",
    }),

    # 4. Saijin / honzon — P825 coverage + how well referenced it is.
    ("p825_shrines", "Saijin: P825 on shrines", {
        "items": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P825 ?v }}",
        "stmts": f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P825 ?st }}",
        "referenced": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P825 ?st .
                          ?st prov:wasDerivedFrom ?r }}""",
    }),
    ("p825_temples", "Honzon: P825 on temples", {
        "items": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; wdt:P825 ?v }}",
        "stmts": f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; p:P825 ?st }}",
        "referenced": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; p:P825 ?st .
                          ?st prov:wasDerivedFrom ?r }}""",
    }),

    # 5. Shrine ranking P13723 (Emma's property proposal) + P459 method.
    ("p13723", "Shrine ranking P13723 + P459", {
        "items": "SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x p:P13723 ?st }",
        "stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P13723 ?st }",
        "with_p459": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P13723 ?st . ?st pq:P459 ?m }",
        "without_p459": """SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P13723 ?st .
                           FILTER NOT EXISTS { ?st pq:P459 ?m } }""",
        "referenced": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P13723 ?st . ?st prov:wasDerivedFrom ?r }",
        "legacy_on_p1552": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P1552 ?v .
                               ?v wdt:P31/wdt:P279* wd:Q11640432 }}""",
    }),

    # 6. Court rank P14005 (Emma's property proposal).
    ("p14005", "Japanese court rank P14005", {
        "items": "SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x p:P14005 ?st }",
        "stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P14005 ?st }",
        "referenced": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P14005 ?st . ?st prov:wasDerivedFrom ?r }",
        "distinct_ranks": "SELECT (COUNT(DISTINCT ?v) AS ?n) WHERE { ?x p:P14005/ps:P14005 ?v }",
        "on_humans": "SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x p:P14005 ?st ; wdt:P31 wd:Q5 }",
        "on_shrines": f"SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x p:P14005 ?st ; wdt:P31 wd:{SHRINE} }}",
    }),

    # 7. Engishiki list membership — ONE clean P361 with an ordinal.
    ("list_membership", "Engishiki list membership: one P361 + P1545", {
        "items": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P361 ?l }}""",
        "stmts": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P361 ?st }}""",
        "with_ordinal": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P361 ?st .
                            ?st pq:P1545 ?o }}""",
        "items_with_multiple": f"""SELECT (COUNT(?s) AS ?n) WHERE {{ {{ SELECT ?s (COUNT(?l) AS ?c) WHERE {{
                                   ?s wdt:P31 wd:{SHRINE} ; wdt:P361 ?l }} GROUP BY ?s HAVING(?c>1) }} }}""",
    }),

    # 8. Shikinai Ronsha — P460 + role qualifiers, Engishiki claims deprecated.
    ("ronsha", "Shikinai Ronsha: P460 + roles, Engishiki deprecated", {
        "ronsha": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{RONSHA} }}",
        "with_p460": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{RONSHA} ; wdt:P460 ?v }}",
        "p460_with_p2868": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{RONSHA} ; p:P460 ?st .
                               ?st pq:P2868 ?r }}""",
        "p460_with_p3831": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{RONSHA} ; p:P460 ?st .
                               ?st pq:P3831 ?r }}""",
        "deprecated_items": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{RONSHA} ; ?p ?st .
                                ?st wikibase:rank wikibase:DeprecatedRank }}""",
    }),

    # 9. Sangō — P1448 + P3831=Q11058522. Zero uses existed before this model.
    ("sango", "Sangō: P1448 + P3831=Q11058522", {
        "stmts": "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?x p:P1448 ?st . ?st pq:P3831 wd:Q11058522 }",
        "on_temples": f"""SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?x wdt:P31 wd:{TEMPLE} ; p:P1448 ?st .
                          ?st pq:P3831 wd:Q11058522 }}""",
        "temple_p1448_all": f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?x wdt:P31 wd:{TEMPLE} ; p:P1448 ?st }}",
    }),

    # 10. Souken — P571 inception coverage.
    ("p571", "Souken: P571 inception", {
        "shrines": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P571 ?d }}",
        "temples": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; wdt:P571 ?d }}",
    }),

    # 11. The cross-wiki identifiers.
    ("identifiers", "Cross-wiki identifiers on shrines", {
        "p11250": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P11250 ?v }}",
        "p6262": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P6262 ?v }}",
        "p13677": f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P13677 ?v }}",
    }),

    # 12. English labels — the label pipeline's own coverage measure.
    ("en_labels", "English label coverage", {
        "shrines_en": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{SHRINE} ; rdfs:label ?l .
                          FILTER(LANG(?l)="en") }}""",
        "temples_en": f"""SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; rdfs:label ?l .
                          FILTER(LANG(?l)="en") }}""",
    }),
]

# Attribution sampling: (label, SPARQL returning ?s, property to attribute).
ATTRIBUTION = [
    ("reisai P837", f"SELECT ?s WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P837 ?st . "
                    f"?st pq:P3831 wd:Q11385469 }} LIMIT 400", "P837"),
    ("bunrei P612", f"SELECT ?s WHERE {{ ?s wdt:P31 wd:{SHRINE} ; p:P612 ?st . "
                    f"?st pq:P1013 wd:Q195793 }} LIMIT 400", "P612"),
    ("saijin P825", f"SELECT ?s WHERE {{ ?s wdt:P31 wd:{SHRINE} ; wdt:P825 ?d }} LIMIT 400", "P825"),
    ("honzon P825 (temples)",
     f"SELECT ?s WHERE {{ ?s wdt:P31 wd:{TEMPLE} ; wdt:P825 ?d }} LIMIT 400", "P825"),
    ("ranking P13723", "SELECT ?s WHERE { ?s p:P13723 ?st } LIMIT 400", "P13723"),
    ("court rank P14005", "SELECT ?s WHERE { ?s p:P14005 ?st } LIMIT 400", "P14005"),
]


def revision_users(qid, prop, cap=500):
    """Users of the revisions whose auto-comment names `prop` on this item."""
    url = WD_API + "?" + urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "titles": qid,
        "rvprop": "user|comment", "rvlimit": cap, "rvdir": "newer",
        "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except Exception:
        return []
    out = []
    for pg in d.get("query", {}).get("pages", []):
        for rev in pg.get("revisions", []):
            c = rev.get("comment", "")
            if re.search(r"\bProperty:%s\b" % prop, c) or re.search(r"\b%s\b" % prop, c):
                out.append(rev.get("user", "?"))
    return out


def run_attribution(sample_size):
    results = {}
    for label, query, prop in ATTRIBUTION:
        rows = wdqs(query)
        if not rows:
            results[label] = {"error": "query failed/empty"}
            continue
        qids = [r["s"]["value"].rsplit("/", 1)[-1] for r in rows]
        random.seed(20260728)
        sample = random.sample(qids, min(sample_size, len(qids)))
        first, everyone = {}, {}
        for qid in sample:
            users = revision_users(qid, prop)
            if users:
                first[users[0]] = first.get(users[0], 0) + 1
            for u in set(users):
                everyone[u] = everyone.get(u, 0) + 1
            time.sleep(0.3)
        results[label] = {"sampled": len(sample), "pool": len(qids),
                          "first_toucher": first, "any_toucher": everyone}
        print(f"  {label}: sampled {len(sample)} of {len(qids)} — "
              f"introduced by {sorted(first.items(), key=lambda kv: -kv[1])[:4]}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attribution", action="store_true",
                    help="sample revision histories to attribute the statements")
    ap.add_argument("--sample", type=int, default=12, help="items per attribution sample")
    ap.add_argument("--json", metavar="PATH", help="write raw results as JSON")
    args = ap.parse_args()

    out = {}
    for key, title, metrics in CHECKS:
        print(f"[{key}] {title}", flush=True)
        row = {}
        for metric, query in metrics.items():
            n = count(query)
            row[metric] = n if n is not None else "WDQS timeout"
            print(f"    {metric:22} {row[metric]}", flush=True)
            time.sleep(0.4)
        out[key] = row

    if args.attribution:
        print("\n=== attribution sampling ===", flush=True)
        out["attribution"] = run_attribution(args.sample)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
