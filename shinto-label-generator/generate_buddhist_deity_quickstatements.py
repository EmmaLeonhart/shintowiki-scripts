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
    bare_name, zh_map, hanja_read, clean_name, looks_romaji,
    sparql_qids, fetch_labels, write_qs, ZH_CODES,
)
import sanskrit_translit

HERE = os.path.dirname(os.path.abspath(__file__))
CLASS = "Q65122124"

# For a SANSKRIT-named deity: the Sanskrit engine handles these scripts; the true
# Latin-script langs get the name verbatim; CJK from the kanji; these non-Latin
# scripts aren't in the Sanskrit module yet, so they're skipped (honest gap).
SANSKRIT_SCRIPTS = sanskrit_translit.SUPPORTED   # hi mai mr bn as ru uk el ar arz fa ur he tok
LATIN = set(COVERED) - SANSKRIT_SCRIPTS - set(ZH_CODES) - {"ko"}
SEWI = "jan sewi "   # toki pona deity classifier (jan=person + sewi=sacred)


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

    def emit_zh_ko(qid, ja, existing):
        zh_src = f'ja kanji "{ja}"'                 # CJK derives from the kanji
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab, zh_src))
        if "ko" in covered and "ko" not in existing:
            ko = hanja_read(ja)
            if ko:
                lines.append((qid, "ko", ko, f'ja kanji "{ja}" (hanja)'))

    lines, jp, skt, no_en = [], 0, 0, 0
    for qid, d in items.items():
        en, ja, existing = d["en"], d["ja"], d["langs"]
        src = clean_name(en)
        if not src:
            no_en += 1                              # only CJK/ko from kanji are safe
            emit_zh_ko(qid, ja, existing)
        elif looks_romaji(src):
            jp += 1                                 # JP-NAMED -> Japanese engine
            rom_src = f'romaji "{src}"'             # provenance: JP-named, from the en romaji
            for lang in covered:
                if lang in existing or lang in ZH_CODES:
                    continue
                lab = bare_name(lang, src, ja, ko_mode="phonetic")
                if lab:
                    if lang == "tok":               # deities take the sewi classifier
                        lab = SEWI + lab
                    lines.append((qid, lang, lab, rom_src))
            zh_src = f'ja kanji "{ja}"'
            for code, lab in zh_map(ja).items():
                if code in covered and code not in existing and lab:
                    lines.append((qid, code, lab, zh_src))
        else:
            skt += 1                                # SANSKRIT -> Sanskrit engine
            skt_src = f'Sanskrit "{src}"'           # provenance: Sanskrit-named source
            for lang in LATIN:                      # true Latin scripts: verbatim
                if lang in covered and lang not in existing:
                    lines.append((qid, lang, src, skt_src))
            for lang in SANSKRIT_SCRIPTS:           # Devanagari/Bengali/Cyrillic/Greek/tok
                if lang in covered and lang not in existing:
                    lab = sanskrit_translit.sanskrit(src, lang)
                    if lab:
                        if lang == "tok":
                            lab = SEWI + lab
                        lines.append((qid, lang, lab, skt_src))
            emit_zh_ko(qid, ja, existing)           # CJK + ko from kanji

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "buddhist_deity_labels.txt")
    write_qs(outpath, lines)
    print(f"\nJP-named={jp} Sanskrit={skt} no-en={no_en}. Wrote {len(lines)} labels -> {outpath}")
    for qid, lang, lab, *_ in lines:   # spot-check Indra + Varuna across scripts
        if qid in ("Q128335", "Q1001037") and lang in ("la", "ru", "el", "hi"):
            print(f"  {qid} {lang}: {lab}")


if __name__ == "__main__":
    main()
