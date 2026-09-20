#!/usr/bin/env python3
"""
dedupe_en_label_files.py
========================
One ``Len`` line per item across the English-label atomic files — the OUTPUT-side
counterpart to ``select_shrines_to_translate.EXCLUDE_FILES``.

## Why this exists

``EXCLUDE_FILES`` stops the LLM stage picking an item some earlier stage already
covers. That is the **input** side, and it is the only guard the pipeline had.
Nothing ever checked the **output**: two ``Len`` lines for one QID in two atomic
files are both valid QuickStatements, the daily drip submits both, and whichever
runs second wins — arbitrarily, with no error anywhere.

It surfaced on 2026-09-19 when ``staged_readings`` let Stage 1 reach 1,406 items
Stage 2 had already claimed: **959 collisions at once**. It recurred on the very
next tick, 32 more, when the designated-city/ward rule added 32 readings. Two
occurrences in two changes is a process, not an accident, so it gets a tool.

## ⭐ Replaces ``dedup_sonnet_labels.py``, which covered a third of the problem

That script pruned ONE file — ``en_labels_sonnet.txt`` — against a hardcoded
``HIGHER_PRIORITY`` list, and the list had never learned about temples:

    HIGHER_PRIORITY = ["en_labels.txt", "kana_en_labels.txt",
                       "identical_name_en_labels.txt"]

``temple_en_labels.txt``, ``temple_identical_name_en_labels.txt`` and
``tenjinsha_en_labels.txt`` were all absent, so **13 temple/LLM collisions were
live** and the prune could never have found them. Two tools with overlapping jobs
and different file lists is exactly how a list goes stale, so there is now one
tool and one list, and a test asserts the guard watches the same files it does.

⚠ It also could not see the Stage 1 vs Stage 2 case at all, because it only ever
rewrote the Sonnet file. That case is normally prevented at generation time —
Stage 2's ``load_targets`` excludes what Stage 1 covers — but every step in
``generate-shrines-missing-en-label.yml`` is ``continue-on-error: true`` and
Stage 2's own docstring says SPARQL is "frequently 503/504", so a Stage 2 file
left stale beside a freshly advanced Stage 1 is an ordinary Tuesday.

## The precedence, and why it is this order

    1. kana_en_labels / temple_en_labels / tenjinsha_en_labels
       Deterministic, from the item's OWN reading. `tenjinsha` is the same thing
       with a hand-checked split (天神 + 社, not 天 + 神社).
    2. identical_name_en_labels / temple_identical_name_en_labels
       Reuse of a name-mate's existing label. Right shape, but it is another
       item's reading.
    3. en_labels
       An external page title. Real, but it carries parenthetical disambiguators
       the rest of the pipeline deliberately strips.
    4. en_labels_sonnet
       Machine translation. The stage everything else exists to keep work away
       from — its own generator's docstring says so.

⭐ Deterministic beats reuse because the reading is the ITEM'S. Where the two
disagree it is mostly macrons (Stage 1 derives from kana and writes none, Stage 2
inherits them from whatever another item carries on Wikidata) and sometimes a
genuine reading split — 小高 as Kodaka or Otaka, 円福寺 as Enpuku-ji or Enfuku-ji.
There Stage 1 has the National Tax Agency registry and Stage 2 has a guess from a
name-mate, and Emma's 2026-08-24 ruling makes the registry authoritative.

⛔ This only ever REMOVES a superseded line. It never rewrites a label, never
picks between two labels of the same rank, and never touches a file that is not
listed — a QID appearing twice inside ONE file is a different defect and is left
alone for the generator that wrote it.

Usage:
    python dedupe_en_label_files.py            # rewrite the files
    python dedupe_en_label_files.py --check    # report only, exit 1 if any found
"""

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Earliest wins. Files within one tuple are the same rank and never override
# each other — they cover disjoint populations (shrines / temples / 天神社).
PRECEDENCE = (
    ("kana_en_labels.txt", "temple_en_labels.txt", "tenjinsha_en_labels.txt"),
    ("identical_name_en_labels.txt", "temple_identical_name_en_labels.txt"),
    ("en_labels.txt",),
    ("en_labels_sonnet.txt",),
)

FILES = [name for rank in PRECEDENCE for name in rank]
RANK = {name: i for i, rank in enumerate(PRECEDENCE) for name in rank}

_LEN = re.compile(r"^(Q\d+)\|Len\|")
_QID = re.compile(r"^(Q\d+)\|")


def owners(base=HERE):
    """{qid: {file: rank}} for every ``Len`` line in the listed files."""
    out = {}
    for name in FILES:
        path = os.path.join(base, name)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                m = _LEN.match(line.strip())
                if m:
                    out.setdefault(m.group(1), {})[name] = RANK[name]
    return out


def superseded(base=HERE):
    """{file: {qid}} — lines a higher-precedence file already covers."""
    drop = {}
    for qid, where in owners(base).items():
        if len(where) < 2:
            continue
        best = min(where.values())
        for name, rank in where.items():
            if rank > best:
                drop.setdefault(name, set()).add(qid)
    return drop


def apply(drop, base=HERE):
    """Remove every line whose QID is listed for that file. Returns {file: count}.

    ⚠ Removes the item's OTHER lines in that file too (``Aen`` aliases), because
    an alias belongs to the label it was generated beside.
    """
    removed = {}
    for name, qids in drop.items():
        path = os.path.join(base, name)
        lines = io.open(path, encoding="utf-8").read().splitlines()
        kept = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue          # blank lines dropped, as the old tool did
            m = _QID.match(stripped)
            if m and m.group(1) in qids:
                continue
            kept.append(line)
        if len(kept) != len(lines):
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                "\n".join(kept) + ("\n" if kept else ""))
        removed[name] = len(lines) - len(kept)
    return removed


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="Report only; exit 1 if anything is superseded.")
    args = ap.parse_args()

    drop = superseded()
    if not drop:
        print("No item carries an en label in more than one file.")
        return 0
    total = sum(len(v) for v in drop.values())
    print("%d superseded en-label lines:" % total)
    for name in FILES:
        if name in drop:
            print("  %-38s %4d" % (name, len(drop[name])))
    if args.check:
        return 1
    for name, n in apply(drop).items():
        print("  rewrote %-36s -%d lines" % (name, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
