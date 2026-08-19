#!/usr/bin/env python3
"""
generate_bunrei_qualifier_repair.py
====================================
Self-healing pass for the bunrei model (Emma 2026-07-07): every shrine P612
(mother house) statement is supposed to be a SINGLE statement carrying the
P1013 (criterion used) = Q195793 (Bunrei) qualifier. Bare P612 statements
appear when a QS line partially fails (statement created, qualifier-add lost)
or when statements are made by hand — this generator finds every bare one via
SPARQL and emits qualifier-add lines. QuickStatements matches the existing
statement by value and adds the qualifier, so the lines are idempotent and
atomic (safe for the daily drip).

Output: bunrei_qualifier_repair.txt
    <shrine>|P612|<head>|P1013|Q195793
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bunrei_qualifier_repair.txt")
# query-main split endpoint: query.wikidata.org is 429-outaged (2026-07-06+)
WDQS = "https://query-main.wikidata.org/sparql"
UA = f"shintowiki-bunrei/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"

QUERY = """
SELECT ?shrine ?head WHERE {
  ?shrine wdt:P31 wd:Q845945 ; p:P612 ?st .
  ?st ps:P612 ?head .
  FILTER NOT EXISTS { ?st pq:P1013 ?x }
}
"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    url = WDQS + "?" + urllib.parse.urlencode({"query": QUERY, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    wd_pace(SPARQL_INTERVAL)
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    lines = sorted({
        f"{b['shrine']['value'].rsplit('/', 1)[-1]}|P612|"
        f"{b['head']['value'].rsplit('/', 1)[-1]}|P1013|Q195793"
        for b in rows})
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} bare P612 statements -> qualifier-add lines -> {OUT}")


if __name__ == "__main__":
    main()
