"""
Generate multi-language labels for shrine ranks (社格) — Kanpei Taisha,
Kokuhei Shōsha, Ichinomiya, Myōjin Taisha, … the shrine-ranking/classification
concepts that seeded the BFS.

Bare-term transliteration (no affix), reusing translit_common. Ranks are
Sino-Japanese compounds, so Korean uses the HANJA (sino-Korean) reading rather
than the phonetic one; ranks whose only label is English (e.g. "Unranked
shrines") still get CJK from the kanji but no phonetic transliteration.

Source: Wikidata items that are P31/P279* of shrine rank (Q10444029).
Non-destructive: emits only (item, lang) pairs the item lacks.

Output: quickstatements/shrine_rank_labels.txt
"""

import os
import sys

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, romaji_source, sparql_qids, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
RANK_CLASS = "Q10444029"


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)
    # The rank CONCEPTS are direct instances of "shrine rank" (Kanpei Taisha,
    # Ichinomiya, …). P31/P279* would instead pull in every shrine modelled with
    # a rank as its P31 — those are already-covered shrines, not ranks.
    print(f"Querying Wikidata for shrine ranks (P31 wd:{RANK_CLASS})...")
    qids = sparql_qids(f"?item wdt:P31 wd:{RANK_CLASS} .")
    print(f"  {len(qids)} rank items. Fetching labels...")
    items = fetch_labels(qids)

    lines = []
    per_lang = {}
    for qid, d in items.items():
        ja = d["ja"]
        existing = d["langs"]
        romaji = romaji_source(d["en"], ja)
        if romaji:
            for lang in covered:
                if lang in existing or lang in ZH_CODES:
                    continue
                lab = bare_name(lang, romaji, ja, ko_mode="hanja")
                if lab:
                    lines.append((qid, lang, lab))
                    per_lang[lang] = per_lang.get(lang, 0) + 1
        elif "ko" in covered and "ko" not in existing:
            # no romaji, but the kanji still yields a sino-Korean reading
            lab = bare_name("ko", "", ja, ko_mode="hanja")
            if lab:
                lines.append((qid, "ko", lab))
                per_lang["ko"] = per_lang.get("ko", 0) + 1
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab))
                per_lang[code] = per_lang.get(code, 0) + 1

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "shrine_rank_labels.txt")
    write_qs(outpath, lines)

    print(f"\nWrote {len(lines)} QuickStatements ({len(per_lang)} languages) to {outpath}")
    print(f"  {len(items)} rank items.")
    print("\n--- sample ---")
    shown = 0
    for qid, lang, lab in lines:
        if lang in ("de", "ru", "el", "hi", "ar", "zh", "ko", "tok") and shown < 24:
            print(f"  {qid:12s} {lang:6s} | {lab}")
            shown += 1


if __name__ == "__main__":
    main()
