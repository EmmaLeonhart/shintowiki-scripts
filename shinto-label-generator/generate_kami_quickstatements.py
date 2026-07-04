"""
Generate multi-language labels for kami (Shinto deities).

Kami names are bare proper names (no "Shrine"/"Temple" affix), so this is pure
name transliteration into every covered language, reusing translit_common.
Korean uses the PHONETIC reading (like Japan shrines), CJK from the JP kanji.

Source: Wikidata items that are P31/P279* of kami (Q524158).
Non-destructive: emits a label only for (item, lang) pairs the item lacks.

Output: quickstatements/kami_labels.txt
"""

import os
import sys
import io

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, romaji_source, sparql_qids, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
KAMI_CLASS = "Q524158"


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)
    print(f"Querying Wikidata for kami (P31/P279* wd:{KAMI_CLASS})...")
    qids = sparql_qids(f"?item wdt:P31/wdt:P279* wd:{KAMI_CLASS} .")
    print(f"  {len(qids)} kami items. Fetching labels...")
    items = fetch_labels(qids)

    lines = []
    per_lang = {}
    no_name = 0
    for qid, d in items.items():
        ja = d["ja"]
        existing = d["langs"]
        romaji = romaji_source(d["en"], ja)   # None when only an English gloss exists
        # Phonetic transliterations need a real romaji reading; CJK comes from
        # the kanji and is emitted regardless.
        if romaji:
            for lang in covered:
                if lang in existing or lang in ZH_CODES:
                    continue
                lab = bare_name(lang, romaji, ja, ko_mode="phonetic")
                if lab:
                    lines.append((qid, lang, lab))
                    per_lang[lang] = per_lang.get(lang, 0) + 1
        else:
            no_name += 1
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab))
                per_lang[code] = per_lang.get(code, 0) + 1

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "kami_labels.txt")
    write_qs(outpath, lines)

    print(f"\nWrote {len(lines)} QuickStatements ({len(per_lang)} languages) to {outpath}")
    print(f"  {len(items)} kami; skipped {no_name} with no usable source name.")
    print("\n--- sample ---")
    shown = 0
    for qid, lang, lab in lines:
        if lang in ("de", "ru", "el", "hi", "ar", "zh", "ko", "tok") and shown < 24:
            print(f"  {qid:12s} {lang:6s} | {lab}")
            shown += 1


if __name__ == "__main__":
    main()
