"""
Labels for ALL the TEXTS in the BFS residual (bfs/texts.tsv, 287 items) —
UNIFIED PIPELINE (2026-07-04 night): two sessions independently built text
labellers within the hour (this filename: 13 curated classical texts, phonetic
ko; the hub session: full 287 scope, gap-aware, Sinitic-title handling, hanja
ko, residue report). Merged here under the filename already wired into
!regenerateQuickStatements.bat. Emma's rule: "most texts are romaji — literally
transliterate into all target languages."

Routing per item, per missing language:
  - Latin-script targets: the canonical title VERBATIM (macrons kept —
    Engishiki Jinmyōchō stays exactly that; titles don't translate).
  - Engine scripts (ru/uk/el/he/ar/arz/fa/ur/hi/mai/mr/bn/as/cs/sl/lt/tok):
    translit_common.bare_name from the romaji reading (looks_romaji en, else
    kana ja romanised).
  - zh family: zh_map from the JAPANESE kanji — fires even when the en title
    is a gloss, not romaji (Sinitic titles like 清史稿 still get the zh set).
  - ko: sino-Korean hanja reading of the kanji title FIRST (the established
    convention for classical texts: 日本書紀 → 일본서기), phonetic koreanize
    fallback. (Deliberate override of the earlier phonetic-only choice.)
Items with no romaji, no kana, and no kanji (Braille standards, empty-label
encyclopedia articles, Wikimedia infra) go to bfs/text_labels_residue.md —
a translation problem for the drift pipeline (queue item 8), never guessed.

Non-destructive. Output: quickstatements/text_labels.txt
"""

import csv
import os
import re
import sys

from language_registry import COVERED, SOURCE_OR_SPECIAL
from translit_common import (
    ZH_CODES, bare_name, clean_name, fetch_labels, hanja_read, koreanize,
    romaji_source, write_qs, zh_map,
)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "bfs", "texts.tsv")
OUT = os.path.join(HERE, "quickstatements", "text_labels.txt")
RESIDUE = os.path.join(HERE, "bfs", "text_labels_residue.md")

_HAN = re.compile(r"[一-鿿㐀-䶿]")

# Languages where bare_name applies a script engine; other covered languages
# are Latin-script and take the title verbatim.
_ENGINE_LANGS = {"cs", "sl", "lt", "ru", "uk", "fa", "ur", "ar", "arz",
                 "hi", "mai", "mr", "bn", "as", "el", "he"}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def target_langs():
    """Every covered language except the sources (ja/en/mul)."""
    return [l for l in COVERED if l not in SOURCE_OR_SPECIAL]


def labels_for_item(en, ja, missing):
    """[(lang, label)] for one text item across the missing languages."""
    romaji = romaji_source(en, ja)
    latin_title = clean_name(en) if clean_name(en) else (romaji or "")
    kanji = ja if ja and _HAN.search(ja) else None

    out = []
    zh_labels = zh_map(kanji) if kanji else {}
    for lang in missing:
        if lang in ZH_CODES:
            if zh_labels.get(lang):
                out.append((lang, zh_labels[lang]))
            continue
        if lang == "ko":
            label = hanja_read(kanji) if kanji else None
            if not label and romaji:
                label = koreanize(romaji)
            if label:
                out.append((lang, label))
            continue
        if lang == "tok":
            if romaji:
                label = bare_name("tok", romaji)
                if label:
                    out.append((lang, label))
            continue
        if not romaji:
            # Latin + engine scripts need a real reading; emitting the
            # English gloss into 40 languages would be fake coverage.
            continue
        if lang in _ENGINE_LANGS:
            label = bare_name(lang, romaji)
        else:
            label = latin_title or romaji
        if label:
            out.append((lang, label))
    return out


def main():
    _utf8()
    rows = []
    with open(SRC, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if re.match(r"^Q\d+$", row.get("qid", "")):
                rows.append(row)
    print(f"texts.tsv: {len(rows)} items")

    info = fetch_labels([r["qid"] for r in rows])

    targets = target_langs()
    lines, residue = [], []
    for r in rows:
        qid = r["qid"]
        en = info.get(qid, {}).get("en", "") or r["en"]
        ja = info.get(qid, {}).get("ja", "") or r["ja"]
        have = info.get(qid, {}).get("langs", set())
        missing = [l for l in targets if l not in have]
        if not missing:
            continue
        got = labels_for_item(en, ja, missing)
        if got:
            for lang, label in got:
                lines.append((qid, lang, label))
        else:
            residue.append((qid, en, ja, r["p31_types"]))

    write_qs(OUT, lines)
    print(f"Wrote {len(lines)} labels for "
          f"{len(set(q for q, _, _ in lines))} texts -> {OUT}")

    with open(RESIDUE, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Texts with no derivable reading (no romaji en, no kana ja, "
                "no kanji)\n\nDeliberate later pass — translation, not "
                "transliteration (drift pipeline, queue item 8). Never "
                "guessed.\n\n")
        f.write("| QID | en | ja | types |\n|---|---|---|---|\n")
        for qid, en, ja, types in residue:
            f.write(f"| {qid} | {en} | {ja} | {types} |\n")
    print(f"Residue (unroutable): {len(residue)} -> {RESIDUE}")


if __name__ == "__main__":
    main()
