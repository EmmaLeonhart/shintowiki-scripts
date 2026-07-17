"""
Generate multi-language labels for Shinto honorifics.

Emma 2026-07-16: "Also adding labels for the honorifics in all covered languages".

Honorific names are bare terms (no "Shrine"/"Temple" affix), exactly like kami
names, so this mirrors generate_kami_quickstatements.py with the class swapped:
pure name transliteration into every covered language via translit_common.
Korean uses the PHONETIC reading; CJK comes from the JP kanji.

Source: Wikidata items that are P31 of Shinto honorific (Q137169543) — the same
class the drip's honorific inference reads, so a honorific Emma mints is picked
up here too with no code change.

Non-destructive: emits a label only for (item, lang) pairs the item lacks.

NO `mul`. Emma 2026-07-16: "mul is not allowed for kami or shrines" — these are
the kami naming vocabulary and follow the same rule. Every language gets its own
transliterated label, which is what the covered-language pipeline is for.

Output: quickstatements/honorific_labels.txt
"""

import os
import sys

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, romaji_source, sparql_qids, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
HONORIFIC_CLASS = "Q137169543"


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)
    print(f"Querying Wikidata for Shinto honorifics (P31 wd:{HONORIFIC_CLASS})...")
    qids = sparql_qids(f"?item wdt:P31 wd:{HONORIFIC_CLASS} .")
    print(f"  {len(qids)} honorific items. Fetching labels...")
    items = fetch_labels(qids)

    lines = []
    per_lang = {}
    no_name = 0
    for qid, d in items.items():
        ja = d["ja"]
        existing = d["langs"]
        romaji = romaji_source(d["en"], ja)   # None when only an English gloss exists
        if romaji:
            src = f'romaji "{romaji}"'          # provenance: phonetic langs derive from this
            for lang in covered:
                if lang in existing or lang in ZH_CODES:   # never touch an existing label
                    continue
                lab = bare_name(lang, romaji, ja, ko_mode="phonetic")
                if lab:
                    lines.append((qid, lang, lab, src))
                    per_lang[lang] = per_lang.get(lang, 0) + 1
        else:
            no_name += 1
        zh_src = f'ja kanji "{ja}"'             # provenance: CJK derives from the kanji
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab, zh_src))
                per_lang[code] = per_lang.get(code, 0) + 1

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "honorific_labels.txt")
    write_qs(outpath, lines)

    print(f"\nWrote {len(lines)} QuickStatements ({len(per_lang)} languages) to {outpath}")
    print(f"  {len(items)} honorifics; skipped {no_name} with no usable source name.")
    print("\n--- sample ---")
    shown = 0
    for qid, lang, lab, *_src in lines:
        if lang in ("de", "ru", "el", "hi", "ar", "zh", "ko") and shown < 24:
            print(f"  {qid:12s} {lang:6s} | {lab}")
            shown += 1


if __name__ == "__main__":
    main()
