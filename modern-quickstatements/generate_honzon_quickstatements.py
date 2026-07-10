#!/usr/bin/env python3
"""
generate_honzon_quickstatements.py
===================================
Import 本尊 (principal image / main object of veneration) from the jawiki
{{日本の寺院}} temple infobox onto Wikidata as P825 (dedicated to) — the temple
sibling of generate_saijin_quickstatements.py, from
`docs/jawiki_infobox_import_review_2026-07.md`.

HIGH-PRECISION design — no name-matching, no guessing:
  * only deities that are WIKILINKED in the 祭神 field are imported;
  * each link target resolves to its Wikidata item via jawiki's own
    pageprops (wikibase_item), following redirects — jawiki's editorial
    linking is the identification, we never match by string;
  * unlinked plain-text deity names are counted and skipped;
  * (shrine, deity) pairs already on Wikidata are skipped (SPARQL set).

Output: honzon_p825.txt — atomic cited lines
    <shrine>|P825|<deity>|S4656|"<jawiki url>"

Usage:
    python generate_honzon_quickstatements.py             # full run
    python generate_honzon_quickstatements.py --limit 200 # sample
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

from infobox_fields import field_pattern

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
TEMPLATE = "Template:日本の寺院"
OUTPUT = os.path.join(HERE, "honzon_p825.txt")

# Same ordered-alternation defect as 祭神: `[^\n|]` halted at the pipe inside the
# first piped wikilink, dropping every later 本尊. See infobox_fields.py.
_FIELD_RE = re.compile(field_pattern("本尊"))
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


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


def resolve_links(titles):
    """{jawiki title -> wikidata QID} for deity link targets (redirects followed)."""
    out = {}
    titles = sorted(titles)
    for i in range(0, len(titles), 50):
        d = _get({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                  "titles": "|".join(titles[i:i + 50]), "redirects": 1})
        qy = d.get("query", {})
        remap = {}
        for r in qy.get("normalized", []) + qy.get("redirects", []):
            remap[r["from"]] = r["to"]
        final = {}
        for t in titles[i:i + 50]:
            ft = t
            seen = set()
            while ft in remap and ft not in seen:
                seen.add(ft)
                ft = remap[ft]
            final[t] = ft
        by_title = {p["title"]: p.get("pageprops", {}).get("wikibase_item")
                    for p in qy.get("pages", {}).values() if "missing" not in p}
        for t, ft in final.items():
            if by_title.get(ft):
                out[t] = by_title[ft]
        time.sleep(0.3)
    return out


def existing_pairs():
    q = "SELECT ?s ?d WHERE { ?s wdt:P31 wd:Q5393308 ; wdt:P825 ?d . }"
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
            for b in rows}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = existing_pairs()
    print(f"{len(have)} existing (temple, honzon) P825 pairs on Wikidata")
    titles = temple_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki temple articles")

    # pass 1: parse fields, collect linked deity targets
    shrine_deities = {}     # (shrine_title, shrine_qid) -> [deity jawiki titles]
    unlinked = no_field = no_qid = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            if not qid:
                no_qid += 1
                continue
            links = [t.strip() for t in _LINK_RE.findall(m.group(1))
                     if t.strip() and not t.startswith(("File:", "ファイル:", "Category:"))]
            plain = _LINK_RE.sub("", m.group(1))
            if re.search(r"[一-龠ぁ-んァ-ヶ]{2,}", plain):
                unlinked += 1   # field also has unlinked names — those are skipped
            if links:
                shrine_deities[(title, qid)] = links
        time.sleep(0.3)
    print(f"{len(shrine_deities)} temples with linked honzon "
          f"(no-field={no_field}, no-QID={no_qid}, fields-with-unlinked-names={unlinked})")

    # pass 2: resolve deity link targets to QIDs
    all_targets = {t for links in shrine_deities.values() for t in links}
    resolved = resolve_links(all_targets)
    print(f"{len(resolved)}/{len(all_targets)} deity link targets resolve to Wikidata items")

    lines, dup = [], 0
    for (title, qid), links in sorted(shrine_deities.items()):
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        for t in dict.fromkeys(links):
            d = resolved.get(t)
            if not d:
                continue
            if (qid, d) in have:
                dup += 1
                continue
            lines.append(f'{qid}|P825|{d}|S4656|"{url}"')
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P825 lines -> {OUTPUT} (already-present pairs skipped: {dup})")


if __name__ == "__main__":
    main()
