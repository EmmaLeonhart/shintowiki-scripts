"""
select_shrines_to_translate.py
==============================
Pick N (default 5) randomly-selected Shinto shrines from the synced
``shrines_missing_en_label.json`` worklist for the daily remote Sonnet
translator (Stage 4) to label. Prints the chosen items as JSON to stdout.

No state file — statefulness is purely presence-based: a shrine is excluded if
its QID already has a line in ANY of the deterministic en-label files, so the
LLM only ever sees the genuine residual (A4):

  - ``en_labels.txt``                — Stage 0, wiki-title lookup
  - ``kana_en_labels.txt``           — Stage 1, deterministic kana
  - ``identical_name_en_labels.txt`` — Stage 2, identical-name reuse
  - ``en_labels_sonnet.txt``         — already LLM-translated, not yet submitted

Once a label lands on Wikidata, the next 24h SPARQL refresh drops the shrine
from the worklist. The result is a self-draining progressive queue that never
re-translates a shrine an earlier stage already handled.

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

HERE = os.path.dirname(os.path.abspath(__file__))
WORKLIST = os.path.join(HERE, "shrines_missing_en_label.json")
QID_RE = re.compile(r"^(Q\d+)\|", re.MULTILINE)

# Every file that already supplies (or will supply) an en label for a QID; the
# LLM must skip all of these so it only translates the true residual.
EXCLUDE_FILES = [
    "en_labels_sonnet.txt",
    "en_labels.txt",
    "kana_en_labels.txt",
    "identical_name_en_labels.txt",
]


def excluded_qids(files=EXCLUDE_FILES, base=HERE):
    """QIDs already covered by any deterministic/pending en-label file."""
    out = set()
    for name in files:
        path = os.path.join(base, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                out |= set(QID_RE.findall(f.read()))
    return out


def select(items, exclude, count, rng=random):
    """Pick up to ``count`` worklist items whose QID isn't excluded."""
    candidates = [it for it in items if it.get("qid") not in exclude]
    return rng.sample(candidates, min(count, len(candidates))) if candidates else []


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=5, help="How many to pick (default 5).")
    args = ap.parse_args()

    if not os.path.exists(WORKLIST):
        print("[]")
        return
    with open(WORKLIST, encoding="utf-8") as f:
        items = json.load(f).get("items", [])

    chosen = select(items, excluded_qids(), args.count)
    print(json.dumps(chosen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
