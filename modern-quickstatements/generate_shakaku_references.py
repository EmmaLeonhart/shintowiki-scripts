#!/usr/bin/env python3
"""
generate_shakaku_references.py
===============================
Reference-backfill for unsourced MODERN shrine rankings (P13723) using the
jawiki {{神社}} infobox 社格 field — build #2 from
`docs/jawiki_infobox_import_review_2026-07.md`. The 2026-07-08 triage found
~92 unsourced modern-rank statements (Son/Ken/Gō-sha …) that the
engishiki-reference generator cannot cover (its scope is engishiki/ritsuryō
values with P13677); where the shrine's own jawiki infobox states the same
rank, the jawiki article is a citable source.

For each unsourced P13723 statement whose value is in RANK_KANJI and whose
item has a jawiki sitelink: fetch the article; if the 社格 field contains the
rank's kanji, emit a reference-add line (QuickStatements matches the existing
statement by value and adds the source — add-only, drip-safe):

    <item>|P13723|<rank QID>|S4656|"<jawiki url>"

Output: shakaku_references.txt.
"""
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
OUTPUT = os.path.join(HERE, "shakaku_references.txt")

# Modern / State-Shinto era ranks, QID -> the kanji the 社格 field would carry.
# Names are deterministic (the QIDs are the repo's own ranking-migration set).
RANK_KANJI = {
    "Q134917284": "村社",       # Son-sha
    "Q134917316": "郷社",       # Gō-sha
    "Q90139226": "県社",        # Ken-sha
    "Q134917282": "府社",       # Fu-sha
    "Q134917281": "国幣小社",   # Kokuhei Shōsha
    "Q135160331": "国幣中社",   # Kokuhei Chūsha (if used)
    "Q10898274": "別表神社",    # Beppyo Shrine
    "Q135009625": "無格社",     # Mukakusha (if used)
}

_SHAKAKU_RE = re.compile(r"\|\s*社格\s*=\s*([^\n]*)")


def sparql(query):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        return json.load(r)["results"]["bindings"]


def unsourced_with_sitelink():
    """[(qid, rank_qid, jawiki_title)] for unsourced modern-rank statements."""
    values = " ".join(f"wd:{v}" for v in RANK_KANJI)
    q = f"""
    SELECT ?item ?rank ?title WHERE {{
      VALUES ?rank {{ {values} }}
      ?item p:P13723 ?st . ?st ps:P13723 ?rank .
      FILTER NOT EXISTS {{ ?st prov:wasDerivedFrom ?ref }}
      ?article schema:about ?item ;
               schema:isPartOf <https://ja.wikipedia.org/> ;
               schema:name ?title .
    }}
    """
    return [(b["item"]["value"].rsplit("/", 1)[-1],
             b["rank"]["value"].rsplit("/", 1)[-1],
             b["title"]["value"]) for b in sparql(q)]


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


def fetch_texts(titles):
    out = {}
    for i in range(0, len(titles), 50):
        d = _get({"action": "query", "prop": "revisions", "rvprop": "content",
                  "rvslots": "main", "titles": "|".join(titles[i:i + 50]),
                  "redirects": 1})
        norm = {}
        for r in d.get("query", {}).get("normalized", []) + d.get("query", {}).get("redirects", []):
            norm[r["from"]] = r["to"]
        rev_norm = {}
        for p in d.get("query", {}).get("pages", {}).values():
            if "missing" not in p and p.get("revisions"):
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
        time.sleep(0.3)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    targets = unsourced_with_sitelink()
    print(f"{len(targets)} unsourced modern-rank statements with a jawiki article")
    texts = fetch_texts(sorted({t for _, _, t in targets}))
    lines, confirmed, unstated = [], 0, 0
    for qid, rank, title in targets:
        text = texts.get(title, "")
        m = _SHAKAKU_RE.search(text)
        field = m.group(1) if m else ""
        if RANK_KANJI[rank] in field:
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            lines.append(f'{qid}|P13723|{rank}|S4656|"{url}"')
            confirmed += 1
        else:
            unstated += 1
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} reference-add lines -> {OUTPUT} "
          f"(infobox confirms rank: {confirmed}; rank not in 社格 field: {unstated})")


if __name__ == "__main__":
    main()
