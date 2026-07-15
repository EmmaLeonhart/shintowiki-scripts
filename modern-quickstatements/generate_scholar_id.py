#!/usr/bin/env python3
"""Add Emma Leonhart's Google Scholar author ID — scheduled, not immediate.

Emma 2026-07-15: add Google Scholar author ID (P1960) `kiJ9hGYAAAAJ` to her own
Wikidata item, `Q140568870` (Emma Leonhart), and **schedule the edit to occur in
two weeks** — 2026-07-29.

Wikidata has exactly one editing path here (the daily QuickStatements pipeline,
CLAUDE.md), so "schedule it" is expressed the documented way: a date-gated
generator. Before `GATE_DATE` it writes an EMPTY atomic file, so the daily editor
has nothing to run; on or after `GATE_DATE` it emits the single QuickStatements
line, which the next `direct_daily_edits.py` run picks up. `scholar_id.txt` is
registered in `direct_daily_edits.ATOMIC_FILES`.

The line is idempotent: `direct_daily_edits.execute_line` checks `find_claim`
first and reports "Skipped (already exists)", so re-emitting it on every run after
the gate date can never create a duplicate statement — no live-state diffing
needed here.

    python generate_scholar_id.py [--out FILE]
"""
import argparse
import datetime
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "scholar_id.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

# Two weeks from the 2026-07-15 request. On/after this UTC date the line is
# emitted; before it, the atomic file is empty. A date rule, not a value to
# revert later (Emma's standing preference — express the exception as a rule).
GATE_DATE = datetime.date(2026, 7, 29)

# (qid, property, value, why). External-id (P1960) values are QS string tokens.
STATIC_EDIT = ("Q140568870", "P1960", '"kiJ9hGYAAAAJ"',
               "Emma Leonhart's Google Scholar author ID")


def qs_line(qid, prop, value):
    return "{}|{}|{}".format(qid, prop, value)


def build(today=None):
    """(lines, notes). Empty before GATE_DATE; the single edit on/after it."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    qid, prop, value, why = STATIC_EDIT
    if today < GATE_DATE:
        return [], ["not yet {} — holding {} {} ({})".format(
            GATE_DATE.isoformat(), qid, prop, why)]
    return [qs_line(qid, prop, value)], ["{} {} — {}".format(qid, prop, why)]


def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lines, notes = build()

    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")
    publish_to_site(path)

    for n in notes:
        print("  " + n)
    print("\n{} line(s) -> {}".format(len(lines), path))
    for l in lines:
        print("   " + l)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
