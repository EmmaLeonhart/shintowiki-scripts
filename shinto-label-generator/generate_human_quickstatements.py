"""
Translate the NAMES of the (Japanese) people in the misc bucket into all covered
languages, using the same bare-name engine as kami (phonetic ko).

Guard: only process a person whose ENGLISH label is itself romanized Japanese
(looks_romaji). That keeps the Japanese figures (Sugawara no Michizane, the
Fujiwara, the emperors) and drops foreign people (Jimmy Wales — a katakana
reading would give "jimiweruzu") and non-name junk (female/male/"Chinese
people"), which the JP-reading engine can't handle.

Source: the `human`-typed rows of bfs/miscellaneous.tsv (levels 0-2).
Non-destructive. Output: quickstatements/human_labels.txt
"""

import os
import re
import sys
import csv

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, looks_romaji, clean_name, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
MISC = os.path.join(HERE, "bfs", "miscellaneous.tsv")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)

    qids = []
    with open(MISC, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if "human" in row["p31_types"] and re.match(r"^Q\d+$", row["qid"]):
                qids.append(row["qid"])
    print(f"{len(qids)} human-typed misc items. Fetching labels...")
    items = fetch_labels(qids)

    lines, per_lang, kept, skipped = [], {}, [], []
    for qid, d in items.items():
        en, ja, existing = d["en"], d["ja"], d["langs"]
        # Only romanized-Japanese personal names; skip foreign/junk.
        if not (en and looks_romaji(en)):
            skipped.append(f"{qid} {en or ja}")
            continue
        kept.append(f"{qid} {en}")
        romaji = clean_name(en)
        for lang in covered:
            if lang in existing or lang in ZH_CODES:
                continue
            lab = bare_name(lang, romaji, ja, ko_mode="phonetic")
            if lab:
                lines.append((qid, lang, lab)); per_lang[lang] = per_lang.get(lang, 0) + 1
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab)); per_lang[code] = per_lang.get(code, 0) + 1

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "human_labels.txt")
    write_qs(outpath, lines)
    print(f"\nKept {len(kept)} Japanese people -> {len(lines)} labels ({len(per_lang)} langs) -> {outpath}")
    print(f"Skipped {len(skipped)} (foreign/non-name): {skipped}")
    print("\nsample:")
    for qid, lang, lab in lines:
        if lang in ("ru", "el", "hi", "ko", "zh") and lab:
            print(f"  {qid} {lang}: {lab}")
            if len([1 for _ in lines[:lines.index((qid,lang,lab))+1]]) > 12:
                break


if __name__ == "__main__":
    main()
