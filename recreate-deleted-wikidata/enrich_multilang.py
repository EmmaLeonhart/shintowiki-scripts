#!/usr/bin/env python3
"""Give every recreation candidate names across many languages (Emma 2026-07-06:
"all recreation candidates should have names across many languages").

Reuses the project's blessed transliteration engine (`shinto-label-generator/
translit_common.py` — the same one that feeds the daily label pipeline): derive the
romaji reading from the en+ja label, then render it into every language in `ALL_LANGS`
(Latin keeps the romaji; Cyrillic/Greek/Arabic/Perso-Arabic/Hebrew/Devanagari/Bengali/
Korean/Toki-Pona transliterate; zh family via the man'yōgana→OpenCC map). Authoritative
fandom langlinks (actual Wikipedia article titles) always WIN over a transliteration.

INPUT/OUTPUT: rewrites each candidate's `items/<QID>.json` with
`enrichment.romaji_reading` + `enrichment.labels` (many languages, each tagged source)
and writes `items/_multilang_summary.md`.

LOCAL only — no network (transliteration is table-driven). Deterministic. Re-runnable.
Requires the label-generator deps: requests hanja opencc-python-reimplemented pykakasi.
"""
import io
import os
import sys
import glob
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "items")
LABEL_GEN = os.path.join(os.path.dirname(HERE), "shinto-label-generator")
sys.path.insert(0, LABEL_GEN)

import translit_common as tc                                  # noqa: E402
from generate_multilang_quickstatements import ALL_LANGS      # noqa: E402


def generate_labels(en, ja, fandom_langlinks):
    """Return (romaji_reading, {lang: {"label":…, "source": "fandom"|"translit"|"native"}})."""
    romaji = tc.romaji_source(en, ja)
    out = {}
    if romaji:
        for lang in ALL_LANGS:
            try:
                v = tc.bare_name(lang, romaji, ja)
            except Exception:
                v = None
            if v:
                out[lang] = {"label": v, "source": "translit"}
        try:
            for zlang, zlabel in tc.zh_map(ja).items():
                out[zlang] = {"label": zlabel, "source": "translit"}
        except Exception:
            pass
    # Native/authoritative overrides win over transliteration.
    if en:
        out["en"] = {"label": en, "source": "native"}
    if ja:
        out["ja"] = {"label": ja, "source": "native"}
    for lang, label in (fandom_langlinks or {}).items():
        out[lang] = {"label": label, "source": "fandom"}
    return romaji, out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    files = sorted(glob.glob(os.path.join(ITEMS_DIR, "Q*.json")))
    counts, rows = [], []
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if not rec.get("recreation_candidate"):
            continue
        fandom = rec.get("fandom") or {}
        en = rec.get("recovered_label") or fandom.get("label")
        ja = fandom.get("langlinks", {}).get("ja")
        romaji, labels = generate_labels(en, ja, fandom.get("langlinks"))
        enr = rec.setdefault("enrichment", {})
        enr["romaji_reading"] = romaji
        enr["labels"] = labels
        enr["label_count"] = len(labels)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        counts.append(len(labels))
        rows.append((rec["qid"], en or "", len(labels)))

    import statistics
    lines = ["# Recreation-candidate multilingual labels — summary\n",
             f"- Candidates given labels: **{len(rows)}**",
             f"- Languages per candidate: min {min(counts)}, median "
             f"{int(statistics.median(counts))}, max {max(counts)}",
             f"- Total label strings generated: **{sum(counts)}**\n",
             "Transliteration engine: `shinto-label-generator/translit_common.py` "
             "(same as the daily label pipeline). Fandom langlinks kept as authoritative "
             "over transliteration.\n",
             "| QID | en label | #languages |", "|---|---|---|"]
    for qid, en, n in sorted(rows, key=lambda r: (-r[2], r[0])):
        lines.append(f"| {qid} | {en} | {n} |")
    with open(os.path.join(ITEMS_DIR, "_multilang_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Gave {len(rows)} candidates labels; median "
          f"{int(statistics.median(counts))} languages each ({sum(counts)} total).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
