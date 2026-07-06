#!/usr/bin/env python3
"""QuickStatements to create Wikidata Wikimedia-category items for shintowiki categories
in [[Category:Categories missing wikidata]] — the tracking category the {{wikidata link}}
template populates when it carries an interwiki but has an empty QID slot, i.e.
``{{wikidata link||ja|Category:X}}`` (Emma 2026-07-05: the standard migrated form).

Per Emma's rule: every item = CREATE + P31=Q4167836 (Wikimedia category) + Sjawiki (the
jawiki category); english-named shinto cats also get an English label (Len); japanese-named
ones are bare (the pipeline links label + shinto/fandom later). Verifies each jawiki category
truly lacks a Wikidata item before emitting (avoid duplicates). Read-only; 429-bail.
Output: jawiki_category_items.txt (human-gated — Emma runs it).
"""
import io
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jawiki_category_items.txt")
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SHINTO = "https://shinto.miraheze.org/w/api.php"
JAWIKI = "https://ja.wikipedia.org/w/api.php"
TRACK = "Category:Categories missing wikidata"
# {{wikidata link | | ja | Category:X }} — empty QID, ja interwiki to a category
_WDL = re.compile(r"\{\{\s*wikidata link\s*\|\s*\|\s*ja\s*\|\s*((?:Category|カテゴリ):[^}|]+)",
                  re.IGNORECASE)
_CJK = re.compile(r"[぀-ヿ㐀-鿿]")


def _get(url, params):
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=60)
    if r.status_code == 429:
        print("  [429] bailing"); sys.exit(2)
    r.raise_for_status()
    return r.json()


def members():
    out, cont = [], {}
    while True:
        p = {"action": "query", "list": "categorymembers", "cmtitle": TRACK,
             "cmlimit": "500", "cmtype": "subcat|page", "format": "json"}
        p.update(cont)
        r = _get(SHINTO, p)
        out += [m["title"] for m in r["query"]["categorymembers"]]
        if "continue" in r:
            cont = r["continue"]
        else:
            break
    return out


def wikitexts(titles):
    """title -> wikitext, batched 50 at a time."""
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        r = _get(SHINTO, {"action": "query", "prop": "revisions", "rvprop": "content",
                          "rvslots": "main", "titles": "|".join(batch), "format": "json"})
        for p in r.get("query", {}).get("pages", {}).values():
            revs = p.get("revisions")
            if revs:
                out[p["title"]] = revs[0]["slots"]["main"]["*"]
        time.sleep(0.3)
    return out


def jawiki_items(ja_titles):
    """ja category title -> True if it already has a Wikidata item, batched."""
    out = {}
    uniq = sorted(set(ja_titles))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get(JAWIKI, {"action": "query", "prop": "pageprops",
                          "titles": "|".join(batch), "format": "json"})
        norm = {n["from"]: n["to"] for n in r.get("query", {}).get("normalized", [])}
        pages = {p["title"]: bool((p.get("pageprops") or {}).get("wikibase_item"))
                 for p in r.get("query", {}).get("pages", {}).values()}
        for t in batch:
            out[t] = pages.get(norm.get(t, t), False)
        time.sleep(0.3)
    return out


def qs(v):
    return '"' + v.replace('"', '\\"') + '"'


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    mem = members()
    print(f"{len(mem)} members in [[{TRACK}]]")
    texts = wikitexts(mem)

    # extract ja category target per shinto category
    targets = {}          # shinto title -> "Category:X" (canonical)
    for t in mem:
        m = _WDL.search(texts.get(t, ""))
        if m:
            tgt = m.group(1).strip().replace("カテゴリ:", "Category:", 1)
            targets[t] = tgt
    print(f"  {len(targets)} carry a ja category interwiki")

    have = jawiki_items(list(targets.values()))
    blocks, skipped = [], 0
    for t, tgt in targets.items():
        if have.get(tgt):
            skipped += 1; continue     # jawiki cat already has an item → don't duplicate
        name = t.split(":", 1)[1] if ":" in t else t
        lines = ["CREATE", "LAST\tP31\tQ4167836", f"LAST\tSjawiki\t{qs(tgt)}"]
        if not _CJK.search(name):
            lines.append(f"LAST\tLen\t{qs('Category:' + name)}")
        blocks.append("\n".join(lines))

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Wikimedia-category items for shintowiki categories in "
                 "[[Category:Categories missing wikidata]] ({{wikidata link||ja|Category:X}}).\n"
                 "# english-named get an en label; japanese-named are bare (pipeline links later).\n\n")
        fh.write("\n\n".join(blocks) + ("\n" if blocks else ""))
    print(f"\nWrote {len(blocks)} CREATE blocks → {os.path.relpath(OUT, HERE)} "
          f"({skipped} skipped — jawiki cat already has an item)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
