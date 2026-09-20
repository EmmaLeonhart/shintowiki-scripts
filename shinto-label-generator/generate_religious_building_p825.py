#!/usr/bin/env python3
"""
generate_religious_building_p825.py
===================================
`P825` (dedicated to) for the religious-building corpus, from the dedication the
label already names.

Emma, 2026-09-18: *"using the dedicated to for other ontology not just labels"*.
The morpheme tables have resolved a label to a dedicatee since 2026-09-17; until
2026-09-19 that only ever became a STRING, and a string identifies nobody —
安德肋 is not a value a statement can carry, `Q43399` is.

    Q106484005|P825|Q133704        Martin of Tours
    Q41412170|P825|Q408284         Sacred Heart

## The three pieces, and where each lives

* `religious_building_morphemes.match_dedication()` — WHICH table entry the label
  matched. One implementation of the precedence, shared with the renderer.
* `saint_qids.qid_for_match()` — that entry's validated QID, or None.
* this file — the join, the guards, and the output.

⛔ **Output lands in `modern-quickstatements/`, not beside the labels.** The
label files are drip-fed by `select_label_proposals.py`, which samples 20 a day
from the language files; a statement is not a label and goes on the ordinary
`direct_daily_edits` path like every other `P825` import in the repo.

## What is refused

* **An unvalidated dedicatee.** `saint_qids` covers 62 terms and concepts, every
  one class-checked; the 101-row seed it grew from was 52% wrong, so anything
  outside it is refused rather than looked up here.
* **A dedication naming several saints where any of them is unknown.** Two
  statements where the label names three assert it named two, so it is
  all-or-nothing. Where all of them resolve, `qids_for_match` returns every one
  and this file emits a statement each — `Santi Pietro e Paolo` is two lines.
* ⛔ **A cultural-property designation, or anything under one.** This is the rule
  CLAUDE.md states for `P825` outright: `P825 → Q1188622` (重要文化財) asserts
  "dedicated to Important Cultural Property", which asserts nothing. None of the
  current values is one — they are saints, Marian titles, dogmas and feasts — and
  the assertion is made anyway, because the day a designation enters the QID map
  is the day nobody is looking.

## What this does NOT check

Whether the item already carries the statement. `direct_daily_edits` treats an
already-present value as a success rather than a failure (`tests/
test_already_present_is_not_a_failure.py`), so a re-offered line costs one API
call and changes nothing. Querying 8,080 items to save that would cost more than
it saves and would hammer an endpoint this repo has a rule about.

Usage:
    python generate_religious_building_p825.py [--stats]
"""

import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import religious_building_morphemes as morph      # noqa: E402
import saint_qids as sq                            # noqa: E402
import generate_religious_building_multilang as G  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "modern-quickstatements",
                   "religious_building_p825.txt")

# ⛔ Cultural Property of Japan and every subclass — the root
# `generate_honzon_quickstatements.INVALID_HONZON_ROOTS` blocks, restated here
# because this file emits P825 too and a guard that lives in another module is a
# guard this one does not have.
INVALID_VALUE_ROOTS = {"Q858308"}
# The designations themselves, which is what a lookup would actually surface.
INVALID_VALUES = {"Q1188622",   # 重要文化財 Important Cultural Property
                  "Q1139795",   # 国宝 National Treasure
                  "Q2901860",   # 有形文化財 Tangible Cultural Property
                  "Q858308"}    # 日本の文化財 Cultural Property of Japan


def rows():
    """[(item_qid, dedicatee_qid)] — one statement per DEDICATEE.

    ⚠ An item may appear on more than one line, and that is the point: a church
    dedicated to Peter and Paul carries two P825 statements. The de-duplication
    below is per ITEM reaching this loop twice (stage 1 emitted two Commons
    categories for six of them), not per line.
    """
    src = G.source_labels()
    with io.open(G.CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)
    out, stats = [], collections.Counter()
    seen = set()
    for qid, label in src:
        meta = cache["items"].get(qid) or {}
        if morph.is_category_shaped(label):
            stats["category-shaped"] += 1
            continue
        if not G.building_type(meta, morph.TYPES):
            stats["no P31 mapping"] += 1
            continue
        hit = morph.match_dedication(label)
        if hit is None:
            stats["no dedication matched"] += 1
            continue
        values = sq.qids_for_match(hit)
        if not values:
            stats["dedicatee has no validated QID"] += 1
            continue
        if any(v in INVALID_VALUES for v in values):
            stats["⛔ cultural-property designation refused"] += 1
            continue
        if qid in seen:
            stats["second label for one item"] += 1
            continue
        seen.add(qid)
        for value in values:
            out.append((qid, value))
        stats["emitted"] += 1
        if len(values) > 1:
            stats["  (of which several dedicatees)"] += 1
    return out, stats


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true",
                    help="Report only; write nothing.")
    args = ap.parse_args()

    pairs, stats = rows()
    print("religious-building P825: %d statements" % len(pairs))
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print("  %-38s %6d" % (k, v))
    values = collections.Counter(v for _, v in pairs)
    print("\n%d distinct dedicatees, most common:" % len(values))
    for q, n in values.most_common(8):
        print("  %-11s %5d" % (q, n))

    if args.stats:
        return 0
    lines = ["%s|P825|%s" % (q, v) for q, v in pairs]
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print("\n-> %s" % os.path.relpath(OUT, os.path.dirname(HERE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
