"""
Buddhist deity labels — the split pipeline (generalizes to ALL Buddhist deities,
`P31/P279* Q65122124`, not just the ones in the BFS corpus).

The ENGLISH label is the established international name — Sanskrit for Sanskrit
deities (Varuna, Acala, Śakra), Japanese-romaji for the Japanese-named ones
(Bishamonten). So the pipeline is uniform: use the English name as the source and
transliterate it into every covered language (Latin keeps it; Cyrillic/Arabic/
Devanagari/etc. transliterate; CJK from the kanji). This is why "indora" happened
before — the old code used `romaji_source`, which preferred the KATAKANA Japanese
reading (インドラ→indora) over the English name (Indra). Using English fixes it and
covers all Buddhist deities the same way.

Non-destructive. Output: quickstatements/buddhist_deity_labels.txt
"""

import os
import sys

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, hanja_read, clean_name,
    sparql_qids, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
CLASS = "Q65122124"


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)
    print(f"All Buddhist deities (P31/P279* wd:{CLASS})...")
    qids = sorted(set(sparql_qids(f"?item wdt:P31/wdt:P279* wd:{CLASS} .")))
    print(f"  {len(qids)} deities. Fetching labels...")
    items = fetch_labels(qids)

    lines, with_en, no_en = [], 0, 0
    for qid, d in items.items():
        en, ja, existing = d["en"], d["ja"], d["langs"]
        src = clean_name(en)                 # the established international name
        if src:
            with_en += 1
            for lang in covered:
                if lang in existing or lang in ZH_CODES:
                    continue
                lab = bare_name(lang, src, ja, ko_mode="phonetic")
                if lab:
                    lines.append((qid, lang, lab))
            for code, lab in zh_map(ja).items():   # CJK from the kanji
                if code in covered and code not in existing and lab:
                    lines.append((qid, code, lab))
        else:
            no_en += 1                        # only CJK/ko from kanji are safe
            for code, lab in zh_map(ja).items():
                if code in covered and code not in existing and lab:
                    lines.append((qid, code, lab))
            if "ko" in covered and "ko" not in existing:
                ko = hanja_read(ja)
                if ko:
                    lines.append((qid, "ko", ko))

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "buddhist_deity_labels.txt")
    write_qs(outpath, lines)
    print(f"\n{with_en} with en, {no_en} without. Wrote {len(lines)} labels -> {outpath}")
    for qid, lang, lab in lines:   # spot-check Indra + Varuna across scripts
        if qid in ("Q128335", "Q1001037") and lang in ("la", "ru", "el", "hi"):
            print(f"  {qid} {lang}: {lab}")


if __name__ == "__main__":
    main()
