"""
Item 5 — broaden coverage: Japanese COURT RANKS and BUDDHIST DEITIES, using the
same bare-name engine (translit_common) as kami/shrine-ranks.

- Court ranks: the values of P14005 (Japanese court rank) — 正一位 etc. Sino-
  Japanese terms, so ko uses the hanja reading; CJK from the kanji.
- Buddhist deities: items that are P31/P279* of the Buddhist-deity class
  (resolved by search so we don't hard-guess the QID). Deity NAMES, so ko is
  phonetic.

Non-destructive. Output: quickstatements/courtrank_labels.txt,
quickstatements/buddhist_deity_labels.txt
"""

import os
import sys
import argparse

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, romaji_source, sparql_qids, fetch_labels, write_qs,
    ZH_CODES, _get, API,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def resolve_class(search):
    """First matching entity QID for a class search term (transparent)."""
    data = _get(API, {"action": "wbsearchentities", "search": search,
                      "language": "en", "type": "item", "limit": 5, "format": "json"}).json()
    for hit in data.get("search", []):
        print(f"    search '{search}' -> {hit['id']} ({hit.get('label','')}: {hit.get('description','')})")
    hits = data.get("search", [])
    return hits[0]["id"] if hits else None


def gen(qids, ko_mode, outname, covered):
    items = fetch_labels(qids)
    lines, per_lang = [], {}
    for qid, d in items.items():
        ja, en, existing = d["ja"], d["en"], d["langs"]
        romaji = romaji_source(en, ja)
        if romaji:
            for lang in covered:
                if lang in existing or lang in ZH_CODES:
                    continue
                lab = bare_name(lang, romaji, ja, ko_mode=ko_mode)
                if lab:
                    lines.append((qid, lang, lab)); per_lang[lang] = per_lang.get(lang, 0) + 1
        elif ko_mode == "hanja" and "ko" in covered and "ko" not in existing:
            lab = bare_name("ko", "", ja, ko_mode="hanja")
            if lab:
                lines.append((qid, "ko", lab)); per_lang["ko"] = per_lang.get("ko", 0) + 1
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab)); per_lang[code] = per_lang.get(code, 0) + 1
    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, outname)
    write_qs(outpath, lines)
    print(f"  {len(items)} items -> {len(lines)} labels ({len(per_lang)} langs) -> {outpath}")
    return lines


def main():
    _utf8()
    ap = argparse.ArgumentParser()
    # Buddhist deities are OFF by default: their names are Sanskrit-origin with
    # established international forms (Indra, Avalokiteśvara, Vairocana), but the
    # bare-name engine transliterates the JAPANESE reading — e.g. Indra (Q128335)
    # -> "indora" in Latin, "इनदोर" in Hindi. That's wrong. They need an
    # international/Sanskrit-name source before this can emit non-CJK labels.
    ap.add_argument("--buddhist", action="store_true",
                    help="ALSO emit Buddhist-deity labels (BROKEN for non-CJK — JP reading of Sanskrit names)")
    args = ap.parse_args()
    covered = set(COVERED)

    print("Court ranks (values of P14005)...")
    ranks = sparql_qids("?x wdt:P14005 ?item .")
    print(f"  {len(ranks)} court-rank values.")
    gen(ranks, "hanja", "courtrank_labels.txt", covered)

    if args.buddhist:
        print("\nBuddhist deities (WARNING: non-CJK labels use the JP reading, not the real name)...")
        cls = resolve_class("Buddhist deity")
        if cls:
            deities = sparql_qids(f"?item wdt:P31/wdt:P279* wd:{cls} .")
            print(f"  {len(deities)} Buddhist-deity items (via {cls}).")
            gen(deities, "phonetic", "buddhist_deity_labels.txt", covered)
        else:
            print("  could not resolve a Buddhist-deity class; skipped.")


if __name__ == "__main__":
    main()
