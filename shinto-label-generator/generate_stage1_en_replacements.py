#!/usr/bin/env python3
"""
generate_stage1_en_replacements.py
==================================
Better English labels for the handful of stage-1 proposals that actually reached
Wikidata before stage 1 was paused.

**Why this is small.** Sizing on 2026-09-18 checked all 22,542 stage-1 proposals
against Wikidata: **93 items carry an English label at all, and 33 match what
stage 1 proposed**. The drip takes 20/day from a ~2.78M-line pool, so almost
nothing had gone out. Emma's call: **replace** them with stage-2 quality English
rather than remove them.

A replacement is emitted only when it is BETTER by a stated test: the current
label has no English type word (it is a German, Italian, Catalan or Latin string
sitting in an `en` label), and the morpheme tables can render a proper English
one. A label that already reads as English is left alone — "Church of Mümliswil"
and "Zangilan Mosque" need nothing.

Output: paused/stage1_en_replacements.txt. Not in the drip.

Usage: python generate_stage1_en_replacements.py
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import religious_building_morphemes as morph  # noqa: E402

SRC = os.path.join(HERE, "paused", "religious_building_en.txt")
LANDED = os.path.join(HERE, "paused", "stage1_landed.json")
CACHE = os.path.join(HERE, "religious_building_cache.json")
OUT = os.path.join(HERE, "paused", "stage1_en_replacements.txt")

# An English type word means the label already reads as English enough to leave.
_TYPE_EN = re.compile(
    r"\b(church|chapel|cathedral|mosque|synagogue|monastery|abbey|basilica"
    r"|temple|oratory)\b", re.I)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    proposed = {}
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r'^(Q\d+)\|Len\|"(.+)"$', line.strip())
            if m:
                proposed[m.group(1)] = m.group(2)
    landed = json.load(open(LANDED, encoding="utf-8"))
    cache = json.load(open(CACHE, encoding="utf-8"))

    ours = [q for q, p in proposed.items()
            if landed.get(q) and landed[q].strip() == p.strip()]
    print("stage-1 labels live on Wikidata: %d" % len(ours))

    lines, skipped = [], {"already English": 0, "cannot render": 0,
                          "no P31 mapping": 0, "same as current": 0}
    for qid in sorted(ours):
        current = landed[qid]
        if _TYPE_EN.search(current):
            skipped["already English"] += 1
            continue
        p31 = (cache["items"].get(qid) or {}).get("p31")
        if not p31 or p31 not in morph.TYPES:
            skipped["no P31 mapping"] += 1
            continue
        better = morph.render_en(current, p31)
        if not better:
            skipped["cannot render"] += 1
            continue
        if better.strip() == current.strip():
            skipped["same as current"] += 1
            continue
        lines.append('%s|Len|"%s"\t# was: %s' % (qid, better, current))

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print("%d replacements -> paused/%s" % (len(lines), os.path.basename(OUT)))
    for k, v in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print("  skipped %-18s %d" % (k, v))
    print("\n⚠ paused/, not the drip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
