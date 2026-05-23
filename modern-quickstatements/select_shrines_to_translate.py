"""
select_shrines_to_translate.py
==============================
Pick N (default 5) randomly-selected Shinto shrines from the synced
``shrines_missing_en_label.json`` worklist for the daily remote Sonnet
translator to label. Prints the chosen items as JSON to stdout.

No state file — statefulness is purely presence-based: a shrine is excluded if
its QID already has a pending line in ``en_labels_sonnet.txt`` (translated but
not yet submitted). Once a label lands on Wikidata, the next 24h SPARQL refresh
drops it from the worklist. The result is a self-draining progressive queue.

Usage:
    python select_shrines_to_translate.py [--count N]
Output (stdout):
    [{"qid": "Q123", "ja": "四所神社", "kana": "ししょじんじゃ"}, ...]
"""

import argparse
import io
import json
import os
import random
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WORKLIST = "shrines_missing_en_label.json"
PENDING_QS = "en_labels_sonnet.txt"
QID_RE = re.compile(r"^(Q\d+)\|", re.MULTILINE)


def pending_qids():
    """QIDs already translated-but-not-yet-submitted (presence-based dedup)."""
    if not os.path.exists(PENDING_QS):
        return set()
    with open(PENDING_QS, encoding="utf-8") as f:
        return set(QID_RE.findall(f.read()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=5, help="How many to pick (default 5).")
    args = ap.parse_args()

    if not os.path.exists(WORKLIST):
        print("[]")
        return
    with open(WORKLIST, encoding="utf-8") as f:
        items = json.load(f).get("items", [])

    skip = pending_qids()
    candidates = [it for it in items if it.get("qid") not in skip]
    chosen = random.sample(candidates, min(args.count, len(candidates))) if candidates else []
    print(json.dumps(chosen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
