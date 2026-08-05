#!/usr/bin/env python3
"""
strip_husk_lines.py
===================
Remove every staged QuickStatement whose SUBJECT is a ブルーノ・プラス-repurposed
husk (queue.md A5; `docs/bruno_plus_analysis_2026-07.md`).

WHY THIS EXISTS AS A SEPARATE STEP. The husks arrive honestly and repeatedly:
each one now IS the 大美和神社 / 近殿神社 / 見光寺 item on Wikidata, so any
generator resolving a jawiki article to a QID by sitelink lands on one. A5's
ruling is that the guard belongs at a single chokepoint rather than in each
generator, "because the next generator written would miss it" — and the same
argument applies here, so this is ONE post-generation sweep over the staged
files, not a filter added to twenty generators.

The submitter's own `item_is_editable()` refusal remains the load-bearing gate;
it is what makes a husk line harmless if one slips through. This step exists so
the staged files are also clean, which is what
`tests/test_repurposed_husks_never_edited.py` asserts — a line sitting in an
atomic file is a line some future path that bypasses the submitter could pick up.

Found again 2026-08-05: the CI regeneration `2dfb736f` re-added 6 husk lines
across honzon_p825.txt, saijin_p825.txt and souken_p571.txt, turning that test
red on main. That recurrence is expected — A5 says so in as many words — which
is exactly why stripping them by hand each time is the wrong shape.

Usage:
    python strip_husk_lines.py            # report only
    python strip_husk_lines.py --apply    # rewrite the files
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Imported rather than duplicated: one list of husks, in the module that owns
# the refusal. A second copy here would drift from the gate it is mirroring.
sys.path.insert(0, HERE)
from direct_daily_edits import REPURPOSED  # noqa: E402

# A QuickStatements line's subject is its first tab/pipe-separated field. A
# REMOVE line is written `-Qxxx|P…`, and the leading `-` is part of the command,
# not the QID — so it is matched and stripped before the lookup.
SUBJECT = re.compile(r"^-?(Q\d+)[|\t]")


def husk_lines(text):
    """[(lineno, line)] whose subject is a husk. Pure — testable without files."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        m = SUBJECT.match(line.strip())
        if m and m.group(1) in REPURPOSED:
            out.append((n, line))
    return out


def strip(text):
    """Text with husk-subject lines removed."""
    keep = [ln for ln in text.splitlines()
            if not (SUBJECT.match(ln.strip())
                    and SUBJECT.match(ln.strip()).group(1) in REPURPOSED)]
    return "\n".join(keep) + ("\n" if keep else "")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the files (default: report only)")
    args = ap.parse_args()

    total, touched = 0, 0
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(HERE, name)
        text = open(path, encoding="utf-8").read()
        found = husk_lines(text)
        if not found:
            continue
        touched += 1
        total += len(found)
        print(f"{name}: {len(found)} husk line(s)")
        for n, line in found:
            print(f"  :{n} {line.strip()[:90]}")
        if args.apply:
            open(path, "w", encoding="utf-8", newline="\n").write(strip(text))

    if not total:
        print("no husk lines staged")
    else:
        print(f"\n{total} husk line(s) across {touched} file(s)"
              f"{' — REMOVED' if args.apply else ' [report only; pass --apply]'}")


if __name__ == "__main__":
    main()
