"""
select_label_proposals.py
=========================
Drip-feed: pick 20 randomly-selected proposed-label QuickStatements from the
merged shinto-label-generator/quickstatements/<lang>.txt files and write them to
``label_proposals_drip.txt`` for the daily QuickStatements submission to push.

Deliberately SLOW at first — only 20/day across ALL languages — so there's time
to see community feedback and adjust the proposals before they go out en masse.
On RAMP_DATE (1 year from setup) it JUMPS to emitting the ENTIRE pool of proposed
labels at once: by then the approach has had a year of review.

No state file: the label-generator's own monthly regen only emits labels that are
still MISSING on Wikidata, so the pool self-drains; re-submitting a label that
already exists is a harmless no-op. Each run overwrites the drip file.

The source files are tab-separated (``Qxxx<TAB>Lid<TAB>"Kuil ..."``) with ``#``
source-comment lines; this converts the chosen lines to the pipe-delimited form
the submitter expects (``Qxxx|Lid|"Kuil ..."``).
"""

import datetime
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
# On/after this date the drip opens fully — emit every proposed label, not just
# COUNT. Set 1 year out (2026-05-23 + 1y) to leave a year of community feedback.
RAMP_DATE = datetime.date(2027, 5, 23)


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

    if datetime.date.today() >= RAMP_DATE:
        # Floodgates open: emit the entire pool (sorted for a stable, churn-free
        # file once we're past the ramp date).
        chosen = sorted(pool)
        mode = f"FULL (>= ramp {RAMP_DATE})"
    else:
        chosen = random.sample(pool, min(COUNT, len(pool)))
        mode = f"drip {COUNT}/day (ramps to full on {RAMP_DATE})"
    OUTPUT.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    print(f"Wrote {len(chosen)} label proposals to {OUTPUT.name} — {mode} "
          f"(pool of {len(pool)} across {len(list(QS_DIR.glob('*.txt')))} languages)")


if __name__ == "__main__":
    main()
