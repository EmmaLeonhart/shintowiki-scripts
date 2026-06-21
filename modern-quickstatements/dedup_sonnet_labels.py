"""
dedup_sonnet_labels.py — A5 priority enforcement.

The English-label stages are disjoint by construction (kana subset, no-kana
subset, residual). But ``en_labels_sonnet.txt`` accumulated LLM translations
over time, before Stages 1/2 existed and before the Stage-4 selector excluded
them (A4). So a shrine can now have BOTH a stale LLM label here AND a
higher-priority deterministic label in ``kana_en_labels.txt`` /
``identical_name_en_labels.txt`` / ``en_labels.txt`` — a double-emission that
would let the lower-priority LLM label win nondeterministically.

This prunes ``en_labels_sonnet.txt`` down to QIDs no higher-priority stage
covers, so deterministic labels always win. The Stage-4 selector (A4) already
prevents the LLM from re-adding them, so the prune is stable.

Usage:
    python dedup_sonnet_labels.py            # rewrite en_labels_sonnet.txt
    python dedup_sonnet_labels.py --stats    # report only, write nothing
"""

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SONNET = os.path.join(HERE, "en_labels_sonnet.txt")
# Higher-priority en-label sources (Stage 0/1/2). LLM (Stage 4) yields to these.
HIGHER_PRIORITY = ["en_labels.txt", "kana_en_labels.txt", "identical_name_en_labels.txt"]
QID_RE = re.compile(r"^(Q\d+)\|")


def _qids_in(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {m.group(1) for m in (QID_RE.match(l) for l in f) if m}


def prune_superseded(sonnet_lines, superseded):
    """Keep only non-blank lines whose QID is not in ``superseded``."""
    kept = []
    for line in sonnet_lines:
        line = line.strip()
        if not line:
            continue
        m = QID_RE.match(line)
        if m and m.group(1) in superseded:
            continue
        kept.append(line)
    return kept


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Report only, write nothing.")
    args = ap.parse_args()

    if not os.path.exists(SONNET):
        print("en_labels_sonnet.txt absent — nothing to prune.")
        return

    superseded = set()
    for name in HIGHER_PRIORITY:
        superseded |= _qids_in(os.path.join(HERE, name))

    with open(SONNET, encoding="utf-8") as f:
        original = f.read().splitlines()
    kept = prune_superseded(original, superseded)
    removed = len([l for l in original if l.strip()]) - len(kept)
    print(f"en_labels_sonnet.txt: {len(kept)} kept, {removed} superseded lines pruned.")

    if args.stats:
        return
    with open(SONNET, "w", encoding="utf-8") as f:
        f.write("\n".join(kept))
        if kept:
            f.write("\n")


if __name__ == "__main__":
    main()
