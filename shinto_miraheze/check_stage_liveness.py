#!/usr/bin/env python3
"""
check_stage_liveness.py
=======================
Does each cloud-fed pipeline stage still have something DRIVING it?

**The hole this covers.** Stage 4 of the English-label pipeline ran as its own
claude.ai routine until 2026-07-27, the day Emma moved Claude accounts. Routines do
not survive an account move; nothing recreated that one, and Stage 4 was absent for
**52 days**. No test in this repo could see it, because the driver was not in this
repo -- and every in-repo symptom looked healthy. Stages 0-2 kept committing daily,
the worklists kept refreshing, the submitter kept reading the file. The only
evidence was `en_labels_sonnet.txt` not growing, against a backlog that grows on its
own.

So this reads the one signal that does cross the boundary: **git history of the
output file**. A stage whose work-file pool has items in it but whose output has not
grown is a stage with nothing driving it.

⚠ **A raw "days since growth" threshold does not work, and the measurement says so.**
On 2026-09-17 `beppyo_p612` had gone **44 days** without growing -- and that is
completely normal, because it is **one** work-file. The drainer takes 5 random items
from ~1,800, so a 1-item category is drawn about once a YEAR. A flat threshold would
report that as a dead stage every single run, which is how a check becomes noise and
then gets ignored.

The rule is therefore relative to the **expected draw rate**:

    expected_days_between_picks = queue_total / (PICKS_PER_DAY * pool_size)

and a stage is only called quiet when its silence exceeds that by ``RATIO``, with a
``MIN_DAYS`` floor so a large pool cannot trip on a couple of quiet days. Measured
against the 2026-09-17 state this reports en_label (52 days against 0.9 expected --
the real gap) and stays silent on beppyo_p612 (44 against 362 expected).

**This is a REPORT, not a gate.** It always exits 0. Nothing in this repo should stop
working because a cloud routine went quiet -- that is the opposite of the fix. It
prints GitHub Actions ``::warning::`` lines so the finding lands on the workflow run
where it is visible, rather than in a log nobody opens.

Usage: python check_stage_liveness.py [--min-days N] [--ratio R] [--quiet]
"""

import argparse
import datetime
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "remote_queue.json")

# How many items the drainer takes per day. Its prompt says 5 at random.
PICKS_PER_DAY = 5
DEFAULT_MIN_DAYS = 14
DEFAULT_RATIO = 10.0

# (work-file directory, output the collector appends to, what the stage is,
#  how many days apart the COLLECTOR runs)
#
# ⚠ The cadence column is not decoration, and leaving it out produced a false
# positive on the first run. `category_translation`'s collector fires only on the
# 1st of the month (wiki-cleanup.yml), so on the 17th its output is necessarily 16
# days stale and that is the system working. An answer can only appear as fast as
# the collector that folds it in, so the draw rate alone is the wrong model.
PAIRS = [
    ("name_in_kana", "modern-quickstatements/name_in_kana.txt",
     "P1814 kana readings", 1),
    ("ronsha_ranking_review", "modern-quickstatements/ronsha_ranking_qualifiers.txt",
     "Shikinai Ronsha candidate rankings", 1),
    ("beppyo_p612", "modern-quickstatements/beppyo_p612.txt",
     "Beppyo mother-house P612", 1),
    ("label_typo_review", "modern-quickstatements/label_typo_fixes.txt",
     "romaji label typo review", 1),
    ("description_enrichment_en", "modern-quickstatements/description_enrichment_en.txt",
     "English descriptions", 1),
    ("en_label", "modern-quickstatements/en_labels_sonnet.txt",
     "English labels (pipeline Stage 4)", 1),
    ("category_translation", "shinto_miraheze/category_moves.csv",
     "Japanese category translation", 31),
]


def outstanding(workdir):
    d = os.path.join(ROOT, workdir)
    if not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith(".wiki")])


def last_growth(rel_path):
    """Date of the most recent commit that ADDED lines to the file, or None.

    Additions, not commits: these files are also rewritten by dedup/strip passes,
    and a commit that only removes lines is not a sign the stage is alive.
    """
    out = subprocess.run(
        ["git", "log", "--date=short", "--format=C%ad", "--numstat", "--", rel_path],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout
    date = None
    for line in out.splitlines():
        if line.startswith("C"):
            date = line[1:].strip()
        elif line.strip() and date:
            added = line.split("\t")[0]
            if added.isdigit() and int(added) > 0:
                return date
    return None


def queue_total():
    if not os.path.exists(QUEUE):
        return 0
    with open(QUEUE, encoding="utf-8") as fh:
        return json.load(fh).get("item_count", 0)


def assess(today=None, min_days=DEFAULT_MIN_DAYS, ratio=DEFAULT_RATIO,
           total=None):
    """One row per stage: {stage, pool, days, expected, threshold, quiet}."""
    today = today or datetime.date.today()
    total = queue_total() if total is None else total
    rows = []
    for workdir, rel_path, what, cadence in PAIRS:
        pool = outstanding(workdir)
        grew = last_growth(rel_path)
        if grew:
            y, m, d = (int(x) for x in grew.split("-"))
            days = (today - datetime.date(y, m, d)).days
        else:
            days = None
        # A pool of 0 means the stage has no work waiting, so silence proves
        # nothing about whether anything is driving it.
        if pool == 0 or total == 0:
            expected = threshold = None
            quiet = False
        else:
            expected = total / float(PICKS_PER_DAY * pool)
            # + cadence: an answered item cannot show up in the output until the
            # collector next runs, so a monthly collector owes nothing for 31 days.
            threshold = max(min_days, ratio * expected + cadence)
            quiet = days is None or days > threshold
        rows.append({
            "stage": workdir, "what": what, "output": rel_path, "pool": pool,
            "last_growth": grew, "days": days, "expected": expected,
            "cadence": cadence, "threshold": threshold, "quiet": quiet,
        })
    return rows


def main():
    # Inside main(): see build_en_label_queue.py.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description="Report cloud-fed stages gone quiet.")
    ap.add_argument("--min-days", type=int, default=DEFAULT_MIN_DAYS)
    ap.add_argument("--ratio", type=float, default=DEFAULT_RATIO)
    ap.add_argument("--quiet", action="store_true",
                    help="Print only the stages that look quiet.")
    args = ap.parse_args()

    rows = assess(min_days=args.min_days, ratio=args.ratio)
    flagged = [r for r in rows if r["quiet"]]

    for r in rows:
        if args.quiet and not r["quiet"]:
            continue
        exp = "-" if r["expected"] is None else f"{r['expected']:.1f}"
        days = "never" if r["days"] is None else str(r["days"])
        mark = "QUIET" if r["quiet"] else "ok"
        print(f"{mark:6} {r['stage']:<26} pool={r['pool']:<5} "
              f"silent={days:<6} expected~{exp}d")

    for r in flagged:
        days = "has never grown" if r["days"] is None else f"{r['days']} days"
        exp = "-" if r["expected"] is None else f"{r['expected']:.1f}"
        print(f"::warning title=Stage may have no driver::{r['output']} "
              f"({r['what']}) {days} without growing, with {r['pool']} items "
              f"waiting -- expected roughly one pick every {exp} days. Check that "
              f"something is still driving this stage.")

    print(f"\n{len(flagged)} of {len(rows)} cloud-fed stages look quiet.")
    # Always 0: this reports, it does not gate. A quiet cloud routine must not
    # stop the rest of the pipeline from running.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
