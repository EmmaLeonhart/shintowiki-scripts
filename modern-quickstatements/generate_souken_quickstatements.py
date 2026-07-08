#!/usr/bin/env python3
"""
generate_souken_quickstatements.py
===================================
Import founding dates from jawiki infoboxes onto Wikidata as P571 (inception)
— shrines ({{神社}} 創建) and temples ({{日本の寺院}} 創建年), from
`docs/jawiki_infobox_import_review_2026-07.md`.

CONSERVATIVE parser (verified against a live 50-article sample): the dominant
clean pattern is an era date with a parenthetical Gregorian year —
「[[貞観 (日本)|貞観]]5年（[[863年]]）」. Only fields that reduce to exactly ONE
unambiguous Gregorian year are imported, at year precision. Skipped by design
(counted, never force-parsed):

  * 伝 / （伝）  — legendary attributions (a future pass may import these with
    the P1480 "presumably" sourcing-circumstances qualifier; Emma's call);
  * 不詳 / 頃 / ? / BC / 年間 — unknown, circa, ranges, era-spans;
  * fields with MULTIPLE distinct years (per-building dates, "before X" notes);
  * fields with no Gregorian year at all (era-only or regnal-only, per jawiki
    citation-style rules some articles deliberately omit the Western year).

Items already carrying P571 are skipped (SPARQL). Output: souken_p571.txt —
    <item>|P571|+YYYY-00-00T00:00:00Z/9|S4656|"<jawiki url>"
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
OUTPUT = os.path.join(HERE, "souken_p571.txt")

CONFIGS = [
    ("Template:神社", r"\|\s*創建\s*=\s*([^\n]*)"),
    ("Template:日本の寺院", r"\|\s*創建年\s*=\s*([^\n]*)"),
]
_YEAR_RE = re.compile(r"(\d{3,4})年")
_SKIP_RE = re.compile(r"伝|不詳|頃|\?|？|紀元前|BC|年間|以前|以降|世紀")


def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def embedded_titles(template):
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": template,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def parse_year(field):
    """The single unambiguous Gregorian year, or None."""
    field = re.sub(r"<!--.*?-->", "", field, flags=re.S)
    field = re.sub(r"\{\{sfn[^}]*\}\}", "", field, flags=re.I)
    if not field.strip() or _SKIP_RE.search(field):
        return None
    years = {int(y) for y in _YEAR_RE.findall(field)}
    years = {y for y in years if 300 <= y <= 2026}   # era-year "5年" noise is <300
    if len(years) != 1:
        return None
    return years.pop()


def items_with_p571():
    q = ("SELECT ?item WHERE { { ?item wdt:P31 wd:Q845945 } UNION "
         "{ ?item wdt:P31 wd:Q5393308 } ?item wdt:P571 [] . }")
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = items_with_p571()
    print(f"{len(have)} shrines/temples already carry P571")
    lines = []
    for template, field_pat in CONFIGS:
        pat = re.compile(field_pat)
        titles = embedded_titles(template)
        if args.limit:
            titles = titles[:args.limit]
        clean = skipped = no_qid = already = 0
        for i in range(0, len(titles), 50):
            for title, qid, text in fetch_batch(titles[i:i + 50]):
                m = pat.search(text or "")
                if not m:
                    continue
                year = parse_year(m.group(1))
                if year is None:
                    skipped += 1
                    continue
                if not qid:
                    no_qid += 1
                    continue
                if qid in have:
                    already += 1
                    continue
                url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                lines.append(f'{qid}|P571|+{year:04d}-00-00T00:00:00Z/9|S4656|"{url}"')
                clean += 1
            time.sleep(0.3)
        print(f"{template}: {len(titles)} articles, clean-year={clean}, "
              f"skipped-ambiguous={skipped}, no-QID={no_qid}, already-had-P571={already}")
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P571 lines -> {OUTPUT}")


if __name__ == "__main__":
    main()
