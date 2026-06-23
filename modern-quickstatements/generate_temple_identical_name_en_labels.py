"""
generate_temple_identical_name_en_labels.py — Stage 2 for Japanese temples.

Temple analogue of ``generate_identical_name_en_labels.py``: for each Japanese
Buddhist temple with a ja label but NO kana and NO en label (the no-kana subset
of ``temples_missing_en_label.json``), reuse the English label of OTHER Japanese
Buddhist temples that share the identical Japanese name. Same principle and same
rules as shrines (dominant reading wins; an alias only when exactly one other
distinct reading) — candidates are restricted to Japanese temples
(``P31=Q5393308`` + ``P17=Q17``) so a shrine's label is never reused on a temple.

Output: ``temple_identical_name_en_labels.txt`` (Len + Aen), in
``submit_daily_batch.ATOMIC_FILES`` and in ``select_shrines_to_translate``'s
EXCLUDE_FILES. Regenerated daily by the worklist workflow.

Usage:
    python generate_temple_identical_name_en_labels.py            # write the .txt
    python generate_temple_identical_name_en_labels.py --stats    # query + report only
    python generate_temple_identical_name_en_labels.py --limit 300
"""

import argparse
import io
import os
import sys

from generate_identical_name_en_labels import run, TEMPLE_TRIPLES

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLE_WORKLIST = os.path.join(HERE, "temples_missing_en_label.json")
OUTPUT_FILE = os.path.join(HERE, "temple_identical_name_en_labels.txt")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Query + report, write nothing.")
    ap.add_argument("--limit", type=int, default=0, help="Cap number of targets (smoke).")
    args = ap.parse_args()
    run(
        worklist=TEMPLE_WORKLIST,
        output_file=OUTPUT_FILE,
        instance_triples=TEMPLE_TRIPLES,
        kind="temples",
        stats=args.stats,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
