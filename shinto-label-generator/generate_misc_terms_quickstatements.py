"""
Transliterate the Japanese-named Shinto TERMS in the misc bucket that aren't
covered by another generator: architecture styles (nagare-zukuri, Kasuga-zukuri,
Sumiyoshi-zukuri…), rituals (Reisai, Okera-sai), sects/schools (koshintō, Sannō
Shintō, State Shinto…), pilgrimages, etc.

The `looks_romaji` guard IS the filter: it passes Japanese-romaji names and
rejects the English descriptive items (Christianity, "portal", "Junior Fourth
Rank") + drift, so no hand-maintained category list is needed. Text items
(bfs/texts.tsv, done by the text labeller) are excluded to avoid double-labelling.

Non-destructive. Output: quickstatements/misc_term_labels.txt
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
TEXTS = os.path.join(HERE, "bfs", "texts.tsv")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _rows(path):
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if re.match(r"^Q\d+$", row.get("qid", "")):
                    out.append(row)
    return out


def main():
    _utf8()
    covered = set(COVERED)
    text_qids = {r["qid"] for r in _rows(TEXTS)}
    # FILTER OFFLINE first: miscellaneous.tsv already has en/ja, so pick the
    # Japanese-romaji terms without any API call; only THEN fetch labels for that
    # small set (needed for the non-destructive existing-language skip).
    # Filter by TYPE, not just romaji shape: looks_romaji alone false-positives on
    # English words that decompose into Japanese syllables ("database", "name",
    # "Japanese"). Require a Shinto-specific P31/P279 type (Shinto architecture,
    # matsuri, Shinto ritual, Shinto sect…) AND the romaji-name shape.
    candidates = [r for r in _rows(MISC)
                  if r["qid"] not in text_qids and r["en"] and looks_romaji(r["en"])
                  and re.search(r"shinto|matsuri", r["p31_types"], re.I)]
    qids = [r["qid"] for r in candidates]
    print(f"{len(candidates)} Japanese-named terms (filtered offline from the tsv). "
          f"Fetching existing labels for just these...")
    items = fetch_labels(qids)

    lines, kept = [], []
    for qid, d in items.items():
        en, ja, existing = d["en"], d["ja"], d["langs"]
        if not (en and looks_romaji(en)):
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
    outpath = os.path.join(outdir, "misc_term_labels.txt")
    write_qs(outpath, lines)
    print(f"\nKept {len(kept)} Japanese-named terms -> {len(lines)} labels -> {outpath}")
    for k in sorted(kept):
        print(f"  {k}")


if __name__ == "__main__":
    main()
