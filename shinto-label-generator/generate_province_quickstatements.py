"""
Generate multi-language labels for the old provinces of Japan (令制国) — the
same province items whose names the Shikinaisha frame already transliterates.

Unlike kami/ranks, a province label is a light frame ("X Province" / "Provinz X"
/ "провинция X"), so this pairs a per-language PROVINCE_FRAME with the shared
name transliteration. CJK comes from the JP kanji label (which already carries
国); Korean uses the phonetic reading + 국 (matching the Shikinaisha convention).

Source: Wikidata items that are P31 province of Japan (Q860290).
Non-destructive: emits only (item, lang) pairs the item lacks. Most provinces
already have labels in the major languages, so yield is mostly the long tail.

Output: quickstatements/province_labels.txt
"""

import os
import re
import sys

from language_registry import COVERED
from translit_common import (
    bare_name, zh_map, koreanize, clean_name, looks_romaji,
    sparql_qids, fetch_labels, write_qs, ZH_CODES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PROVINCE_CLASS = "Q860290"

# Per-language "{X} Province" frame; {n} is the transliterated province name.
# Province words mirror the Shikinaisha frames. CJK codes + ko are handled
# separately (from the kanji), so they are intentionally absent here.
FRAME = {
    "tr": "{n} vilayeti", "de": "Provinz {n}", "nl": "provincie {n}",
    "es": "Provincia de {n}", "it": "Provincia di {n}", "eu": "{n} probintzia",
    "fr": "province de {n}", "pt": "Província de {n}", "vi": "tỉnh {n}",
    "ca": "Província de {n}", "gl": "Provincia de {n}", "sv": "provinsen {n}",
    "nb": "provinsen {n}", "da": "provinsen {n}", "nn": "provinsen {n}",
    "hu": "{n} tartomány", "la": "Provincia {n}", "ast": "Provincia de {n}",
    "sh": "Provincija {n}", "hr": "Provincija {n}", "az": "{n} əyaləti",
    "tl": "Lalawigan ng {n}", "war": "Probinsya han {n}", "min": "Provinsi {n}",
    "eo": "Provinco {n}", "jv": "Provinsi {n}", "ms": "Wilayah {n}",
    "br": "Provins {n}", "ceb": "Lalawigan sa {n}", "pl": "Prowincja {n}",
    "ro": "Provincia {n}", "fi": "{n}n maakunta", "id": "Provinsi {n}",
    "cs": "Provincie {n}", "sl": "Provinca {n}", "lt": "{n} provincija",
    "ru": "Провинция {n}", "uk": "Провінція {n}", "fa": "استان {n}",
    "ur": "صوبہ {n}", "ar": "مقاطعة {n}", "arz": "مقاطعة {n}",
    "hi": "{n} प्रान्त", "mai": "{n} प्रान्त", "mr": "{n} प्रांत",
    "bn": "{n} প্রদেশ", "as": "{n} প্ৰদেশ", "el": "Επαρχία {n}",
    "he": "מחוז {n}", "tok": "ma {n}",
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _province_name(en):
    """'Yamashiro Province' / 'Province of Yamashiro' / 'Yamashiro' -> 'Yamashiro'."""
    s = clean_name(en)
    s = re.sub(r"^Province of\s+", "", s)
    s = re.sub(r"\s+Province$", "", s)
    return s.strip()


def main():
    _utf8()
    covered = set(COVERED)
    print(f"Querying Wikidata for provinces (P31 wd:{PROVINCE_CLASS})...")
    qids = sparql_qids(f"?item wdt:P31 wd:{PROVINCE_CLASS} .")
    print(f"  {len(qids)} province items. Fetching labels...")
    items = fetch_labels(qids)

    lines = []
    per_lang = {}
    for qid, d in items.items():
        ja = d["ja"]
        existing = d["langs"]
        name_en = _province_name(d["en"])
        has_romaji = bool(name_en) and looks_romaji(name_en)

        # Framed transliterations (need a romaji province name)
        if has_romaji:
            for lang, tmpl in FRAME.items():
                if lang not in covered or lang in existing:
                    continue
                n = bare_name(lang, name_en, ja)   # translit or plain romaji
                if n:
                    lines.append((qid, lang, tmpl.format(n=n)))
                    per_lang[lang] = per_lang.get(lang, 0) + 1
            # Korean: phonetic name + 국 (matches the Shikinaisha convention)
            if "ko" in covered and "ko" not in existing:
                k = koreanize(name_en)
                if k:
                    lines.append((qid, "ko", f"{k}국"))
                    per_lang["ko"] = per_lang.get("ko", 0) + 1

        # CJK from the kanji label (already carries 国), regardless of romaji
        for code, lab in zh_map(ja).items():
            if code in covered and code not in existing and lab:
                lines.append((qid, code, lab))
                per_lang[code] = per_lang.get(code, 0) + 1

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "province_labels.txt")
    write_qs(outpath, lines)

    print(f"\nWrote {len(lines)} QuickStatements ({len(per_lang)} languages) to {outpath}")
    print(f"  {len(items)} provinces.")
    print("\n--- sample ---")
    shown = 0
    for qid, lang, lab in lines:
        if lang in ("de", "ru", "el", "fr", "zh", "ko", "tok") and shown < 21:
            print(f"  {qid:12s} {lang:6s} | {lab}")
            shown += 1


if __name__ == "__main__":
    main()
