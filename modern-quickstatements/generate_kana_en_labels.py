"""
generate_kana_en_labels.py — Stage 1 of the English-label pipeline.

Reads the synced worklist ``shrines_missing_en_label.json`` (every Shinto
shrine with a ja label but no en label, kana captured when present) and, for
the kana-bearing subset, deterministically builds the English label via
``kana_english.kana_to_label`` — no LLM. Emits QuickStatements lines:

    Qxxx|Len|"<Stem> Shrine"        (label)
    Qxxx|Aen|"<Stem> Jingu"         (alias, for jingu/taisha only)

to ``kana_en_labels.txt``, which is in ``submit_daily_batch.ATOMIC_FILES`` so
the daily drip submits it. Items whose kana has no recognised shrine suffix, or
whose stem still contains kanji, emit nothing — they fall through to Stage 2+.

This is what removes kana-bearing shrines from the LLM's plate (Stage 4): they
are cheaper and higher-confidence handled here.

Usage:
    python generate_kana_en_labels.py            # write kana_en_labels.txt
    python generate_kana_en_labels.py --stats    # print coverage, write nothing
"""

import argparse
import io
import json
import os
import sys

from kana_english import label_for

WORKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shrines_missing_en_label.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kana_en_labels.txt")


def lines_for_item(item):
    """QuickStatements lines for one worklist item, or [] if Stage 1 can't handle it."""
    kana = (item.get("kana") or "").strip()
    if not kana:
        return []
    result = label_for(item.get("ja", ""), kana)
    if result is None:
        return []
    qid = item["qid"]
    # Guard against any stray double-quote in a label breaking the QS line.
    if '"' in result.label:
        return []
    # Emma 2026-07-06: most-common English label only, NO aliases (pipeline-wide rule).
    return [f'{qid}|Len|"{result.label}"']


def load_worklist():
    if not os.path.exists(WORKLIST):
        return []
    with open(WORKLIST, encoding="utf-8") as f:
        return json.load(f).get("items", [])


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Print coverage stats, write nothing.")
    args = ap.parse_args()

    items = load_worklist()
    with_kana = [it for it in items if (it.get("kana") or "").strip()]
    all_lines = []
    handled = 0
    for it in with_kana:
        lines = lines_for_item(it)
        if lines:
            handled += 1
        all_lines.extend(lines)

    total = len(items)
    print(f"Worklist: {total} shrines missing en label; {len(with_kana)} have kana.")
    print(f"Stage 1 deterministically handled {handled}/{len(with_kana)} kana shrines "
          f"-> {len(all_lines)} QuickStatements lines.")

    if args.stats:
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
        if all_lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
