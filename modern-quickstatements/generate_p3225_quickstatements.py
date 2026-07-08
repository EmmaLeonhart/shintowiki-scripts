#!/usr/bin/env python3
"""
generate_p3225_quickstatements.py
==================================
Import 法人番号 (Japan Corporate Number) from the jawiki {{日本の寺院}} temple
infobox onto Wikidata as P3225 — the first build from
`docs/jawiki_infobox_import_review_2026-07.md` (Emma's jawiki-infobox review,
2026-07-08). Government-issued 13-digit identifier; exact-match, authoritative.

Same shape as the reisai import: walk every jawiki article embedding the
temple infobox, parse the field, skip items that already carry P3225, emit
atomic cited lines:

    <item>|P3225|"<13 digits>"|S4656|"<jawiki url>"

Only clean 13-digit values are emitted (counted, never force-parsed).
Read-only against jawiki. Output: p3225_corporate_numbers.txt.

Usage:
    python generate_p3225_quickstatements.py             # full run
    python generate_p3225_quickstatements.py --limit 100 # sample
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
TEMPLATE = "Template:日本の寺院"
OUTPUT = os.path.join(HERE, "p3225_corporate_numbers.txt")

_FIELD_RE = re.compile(r"\|\s*法人番号\s*=\s*([^\n]*)")
_NUM_RE = re.compile(r"\b(\d{13})\b")


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


def temple_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
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


def items_with_p3225():
    """QIDs that already carry P3225 (any class) — never re-add."""
    q = "SELECT ?item WHERE { ?item wdt:P3225 [] . ?item wdt:P17 wd:Q17 . }"
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}


def parse_number(wikitext):
    m = _FIELD_RE.search(wikitext or "")
    if not m:
        return None
    n = _NUM_RE.search(m.group(1))
    return n.group(1) if n else None


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


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = items_with_p3225()
    print(f"{len(have)} Japanese items already carry P3225")
    titles = temple_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki temple articles")

    lines, no_field, no_qid, already = [], 0, 0, 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            num = parse_number(text)
            if not num:
                no_field += 1
                continue
            if not qid:
                no_qid += 1
                continue
            if qid in have:
                already += 1
                continue
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            lines.append(f'{qid}|P3225|"{num}"|S4656|"{url}"')
        time.sleep(0.3)

    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P3225 lines -> {OUTPUT} "
          f"(no-field/unparsable={no_field}, no-QID={no_qid}, already-had={already})")


if __name__ == "__main__":
    main()
