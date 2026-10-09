#!/usr/bin/env python3
"""Give each Japanese temple labelled "X Temple" in English the mul (multi-language) label "X".

Emma, 2026-10-09: "Toko-in Temple gets a mul label of Toko-in", as one mass QuickStatements
batch, run locally (no CI). Items that already have a mul label are left alone.

    python modern-quickstatements/generate_temple_mul_labels.py
"""
import io
import os
import re
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "temple_mul_labels.txt")
UA = "shintowiki-scripts/1.0 (https://github.com/EmmaLeonhart/shintowiki-scripts; emma@topazcomputing.com)"

QUERY = """
SELECT DISTINCT ?item ?en WHERE {
  ?item wdt:P17 wd:Q17 ;
        wdt:P31/wdt:P279* wd:Q44539 ;
        rdfs:label ?en .
  FILTER(LANG(?en) = "en")
  FILTER(REGEX(?en, " Temple$"))
  FILTER NOT EXISTS { ?item rdfs:label ?m . FILTER(LANG(?m) = "mul") }
}
"""


def main():
    r = requests.get("https://query.wikidata.org/sparql",
                     params={"query": QUERY, "format": "json"},
                     headers={"User-Agent": UA}, timeout=300)
    if r.status_code == 429:
        sys.exit("429 from WDQS; bailing")
    r.raise_for_status()
    rows = r.json()["results"]["bindings"]
    lines = sorted({
        '%s\tLmul\t"%s"' % (b["item"]["value"].rsplit("/", 1)[1],
                             re.sub(r"( Buddhist)? Temple$", "", b["en"]["value"]))
        for b in rows
    })
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(len(lines), "lines ->", OUT)


if __name__ == "__main__":
    main()
