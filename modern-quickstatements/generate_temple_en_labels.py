"""
generate_temple_en_labels.py — deterministic English labels for Japanese temples.

Temple analogue of ``generate_kana_en_labels.py``. Reads the synced worklist
``temples_missing_en_label.json`` (every Japanese Buddhist temple with a ja label
but no en label, kana captured when present) and, for the kana-bearing subset,
deterministically builds the English label via ``temple_english.label_for`` — no
LLM. Emits QuickStatements lines:

    Qxxx|Len|"<Stem>-<suffix> Temple"

to ``temple_en_labels.txt``, which is added to ``submit_daily_batch.ATOMIC_FILES``
so the daily drip submits it. Items whose kana has no recognised temple suffix,
or whose stem still contains kanji, emit nothing — they fall through to the
wiki-title lookup / LLM stages.

Usage:
    python generate_temple_en_labels.py            # write temple_en_labels.txt
    python generate_temple_en_labels.py --stats    # print coverage, write nothing
"""

import argparse
import io
import json
import os
import sys

from temple_english import label_for

WORKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temples_missing_en_label.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temple_en_labels.txt")


def lines_for_item(item):
    """QuickStatements lines for one worklist item, or [] if it can't be handled."""
    kana = (item.get("kana") or "").strip()
    if not kana:
        return []
    result = label_for(item.get("ja", ""), kana)
    if result is None:
        return []
    if '"' in result.label:
        return []
    return [f'{item["qid"]}|Len|"{result.label}"']


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

    print(f"Worklist: {len(items)} temples missing en label; {len(with_kana)} have kana.")
    print(f"Deterministically handled {handled}/{len(with_kana)} kana temples "
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
