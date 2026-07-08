#!/usr/bin/env python3
"""
build_ronsha_ranking_queue.py
==============================
Cloud-RAG work-file builder for the ronsha dedup likelihood rankings (Emma's
[[d:Wikidata:WikiProject Shinto/ronsha deduplication (all unranked)]] list —
"the most important shikinaisha cleanup right now"; triaged 2026-07-08 as
judgment work, not automatable).

Each Shikinai Ronsha (a disputed Engishiki shrine identity) carries P460
(said to be the same as) statements pointing at its candidate real-world
shrines. Existing convention on already-ranked ronsha: qualifier **P1352 = 1
on the LIKELY candidate, P1352 = 0 on the others** (binary, not ordinal).
This builder targets ronsha where NO candidate is ranked yet and writes one
work-file per ronsha into `ronsha_ranking_review/` with candidate context;
the cloud worker researches and fills the ANSWER marker; then
`collect_ronsha_rankings.py` turns answers into qualifier-add QS lines.

Idempotent: skips work-files that already exist (they may hold answers).
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "ronsha_ranking_review")
WDQS = "https://query-main.wikidata.org/sparql"
UA = "shintowiki-ronsha/1.0 (https://shinto.miraheze.org; immanuelleleonhart@gmail.com)"

TASK = (
    "<!-- TASK: this Shikinai Ronsha (disputed Engishiki shrine identity) has "
    "candidate real-world shrines under P460 with NO likelihood ranking. Research "
    "each candidate (jawiki, Kokugakuin database, location vs the Engishiki "
    "province/district, name continuity) and decide which single candidate is the "
    "LIKELIEST true shrine. Fill ANSWER with exactly one of:\n"
    "  LIKELY: <QID of the likeliest candidate>   (only it gets ranked 1; P1352=0 is reserved for legitimate shrines absent from the Kokugakuin database)\n"
    "  UNDECIDABLE: <why no candidate can be preferred>\n"
    "When ANSWER is filled this file is done. -->"
)


def sparql(query):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        return json.load(r)["results"]["bindings"]


def targets():
    q = """
    SELECT ?item ?itemLabel ?itemDesc ?cand ?candLabel ?candDesc ?prefLabel WHERE {
      ?item wdt:P31 wd:Q135038714 . ?item wdt:P31 wd:Q134917286 .
      FILTER EXISTS { ?item p:P460 ?s . ?s ps:P460 ?x .
                      FILTER NOT EXISTS { ?s pq:P1352 ?r } }
      FILTER NOT EXISTS { ?item p:P460 ?s2 . ?s2 pq:P1352 ?r2 }
      ?item p:P460 ?st . ?st ps:P460 ?cand .
      OPTIONAL { ?item schema:description ?itemDesc . FILTER(LANG(?itemDesc)="en") }
      OPTIONAL { ?cand schema:description ?candDesc . FILTER(LANG(?candDesc)="en") }
      OPTIONAL { ?cand wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ;
                 rdfs:label ?prefLabel . FILTER(LANG(?prefLabel)="en") }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
    }
    """
    ronsha = {}
    for b in sparql(q):
        g = lambda k: b.get(k, {}).get("value")
        qid = g("item").rsplit("/", 1)[1]
        rec = ronsha.setdefault(qid, {"label": g("itemLabel"), "desc": g("itemDesc"),
                                      "cands": {}})
        cq = g("cand").rsplit("/", 1)[1]
        c = rec["cands"].setdefault(cq, {"label": g("candLabel"), "desc": g("candDesc"),
                                         "pref": None})
        if g("prefLabel"):
            c["pref"] = g("prefLabel")
    return ronsha


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    ronsha = targets()
    written = skipped = 0
    for qid, rec in sorted(ronsha.items()):
        path = os.path.join(OUTDIR, f"{qid}.wiki")
        if os.path.exists(path):
            skipped += 1
            continue
        lines = [
            f"<!-- RONSHA: https://www.wikidata.org/wiki/{qid} | {rec['label']} | {rec['desc'] or ''} -->",
            "<!-- ANSWER: -->",
            TASK,
            "",
            "== Candidates (P460, all unranked) ==",
        ]
        for cq, c in sorted(rec["cands"].items()):
            pref = f" — {c['pref']}" if c["pref"] else ""
            desc = f" — {c['desc']}" if c["desc"] else ""
            lines.append(f"* [[d:{cq}]] {c['label']}{pref}{desc}")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        written += 1
    print(f"{written} work-files written, {skipped} already existed -> {OUTDIR}")


if __name__ == "__main__":
    main()
