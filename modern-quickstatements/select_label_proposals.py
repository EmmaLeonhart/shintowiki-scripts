"""
select_label_proposals.py
=========================
Drip-feed: pick 20 randomly-selected proposed-label QuickStatements from the
merged shinto-label-generator/quickstatements/<lang>.txt files and write them to
``label_proposals_drip.txt`` for the daily QuickStatements submission to push.

Deliberately SLOW — only 20/day across ALL languages (Emma wants labels to lag
the other QS work). No state file: the label-generator's own monthly regen only
emits labels that are still MISSING on Wikidata, so the pool self-drains;
re-submitting a label that already exists is a harmless no-op. Each run
overwrites the drip file with a fresh random sample.

The source files are tab-separated (``Qxxx<TAB>Lid<TAB>"Kuil ..."``) with ``#``
source-comment lines; this converts the chosen lines to the pipe-delimited form
the submitter expects (``Qxxx|Lid|"Kuil ..."``).
"""

import io
import random
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent          # modern-quickstatements/
REPO_ROOT = SCRIPT_DIR.parent
QS_DIR = REPO_ROOT / "shinto-label-generator" / "quickstatements"
OUTPUT = SCRIPT_DIR / "label_proposals_drip.txt"
COUNT = 20


def main():
    if not QS_DIR.is_dir():
        print(f"No {QS_DIR} (subtree not present?) — writing empty drip file.")
        OUTPUT.write_text("", encoding="utf-8")
        return

    pool = []
    for path in sorted(QS_DIR.glob("*.txt")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                # Normalise tab-delimited QS to the pipe form the submitter parses.
                pool.append(s.replace("\t", "|"))

    if not pool:
        print("Pool empty — writing empty drip file.")
        OUTPUT.write_text("", encoding="utf-8")
        return

    chosen = random.sample(pool, min(COUNT, len(pool)))
    OUTPUT.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    print(f"Wrote {len(chosen)} label proposals to {OUTPUT.name} "
          f"(pool of {len(pool)} across {len(list(QS_DIR.glob('*.txt')))} languages)")


if __name__ == "__main__":
    main()
