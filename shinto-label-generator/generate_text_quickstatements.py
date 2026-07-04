"""
Labels for the Japanese classical TEXTS in the misc bucket (bfs/japanese_texts.tsv)
— the Engishiki family (延喜式, 延喜式神名帳, 神名帳考証) and the Rikkokushi national
histories (続日本紀, 日本後紀, 続日本後紀, 日本文徳天皇実録, 日本三代実録, 類聚国史).

These are Japanese proper-name titles, so the Japanese name engine applies (same
as kami/humans): romaji kept for Latin, transliterated for non-Latin, CJK from
the kanji. `looks_romaji` guard skips the foreign encyclopedias mixed into the file.

Non-destructive. Output: quickstatements/text_labels.txt
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
SRC = os.path.join(HERE, "bfs", "japanese_texts.tsv")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    _utf8()
    covered = set(COVERED)
    qids = []
    with open(SRC, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if re.match(r"^Q\d+$", row["qid"]):
                qids.append(row["qid"])
    print(f"{len(qids)} texts. Fetching labels...")
    items = fetch_labels(qids)

    lines, kept, skipped = [], [], []
    for qid, d in items.items():
        en, ja, existing = d["en"], d["ja"], d["langs"]
        if not (en and looks_romaji(en)):
            skipped.append(f"{qid} {en or ja}")     # foreign encyclopedia etc.
            continue
        kept.append(f"{qid} {en}")
        romaji = clean_name(en)
        for lang in covered:
            if lang in existing or lang in ZH_CODES:
                continue
            lab = bare_name(lang, romaji, ja, ko_mode="phonetic")
            if lab:
                lines.append((qid, lang, lab))
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab))

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "text_labels.txt")
    write_qs(outpath, lines)
    print(f"\nKept {len(kept)} Japanese texts -> {len(lines)} labels -> {outpath}")
    print(f"Skipped {len(skipped)} foreign/non-JP: {skipped}")


if __name__ == "__main__":
    main()
