#!/usr/bin/env python3
"""
generate_reisai_qualifier_repair.py
====================================
Self-healing pass for the reisai model (docs/wikidata_shrine_festival_model.md):
every shrine P837 (day in year for periodic occurrence) statement carries a
P3831 role qualifier — normally Q11385469 (Reisai). A QS partial failure can
land the statement without its qualifier; this generator finds every shrine
P837 statement with NO P3831 qualifier at all and emits qualifier-add lines.
Add-only, idempotent, safe for the random-order daily drip.

Statements that already have any P3831 (Reisai or another role item) are
untouched — role choice is modeling, not repair.

Output: reisai_qualifier_repair.txt
    <shrine>|P837|<day>|P3831|Q11385469
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reisai_qualifier_repair.txt")
# query-main split endpoint: query.wikidata.org is 429-outaged (2026-07-06+)
WDQS = "https://query-main.wikidata.org/sparql"
UA = f"shintowiki-reisai/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"

QUERY = """
SELECT ?shrine ?day WHERE {
  ?shrine wdt:P31 wd:Q845945 ; p:P837 ?st .
  ?st ps:P837 ?day .
  FILTER NOT EXISTS { ?st pq:P3831 ?x }
}
"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    url = WDQS + "?" + urllib.parse.urlencode({"query": QUERY, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    lines = sorted({
        f"{b['shrine']['value'].rsplit('/', 1)[-1]}|P837|"
        f"{b['day']['value'].rsplit('/', 1)[-1]}|P3831|Q11385469"
        for b in rows})
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} bare P837 statements -> qualifier-add lines -> {OUT}")


if __name__ == "__main__":
    main()
