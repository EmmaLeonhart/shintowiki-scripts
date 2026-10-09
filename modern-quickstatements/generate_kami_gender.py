#!/usr/bin/env python3
"""
generate_kami_gender.py
=======================
Step 1 of setting the obvious gender on the kami we created: the ADD generator.

Emma, 2026-10-08, queue item: *"Before the merging, we're going to run through these and see
if there's an obvious gender of the kami that we can apply. Since a lot of them have sex
unknown, but that's just straight up not true ... they have things like Hime in their names."*

The items are the ones in `deity_creates.state`. Measured 2026-10-08: of 191, P21 is
"unknown" (Q24238356) on 161 and absent on 30. This emits `<kami>|P21|Q6581072` (female) or
`<kami>|P21|Q6581097` (male) where the Japanese label carries an obvious marker and the item has
no real P21 yet. A name with markers for both sexes, or for neither, is left alone.

Step 2, `generate_kami_gender_unknown_removals.py`, removes the old P21 = unknown only once a
fresh query confirms the real value landed (CLAUDE.md: add first, remove later, two scripts).

One SPARQL query per run. GENERATOR ONLY: writes `kami_gender.txt` (ATOMIC_FILES).
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import io
import json
import os
import sys

import wdqs_transport

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "deity_creates.state")
OUTPUT = os.path.join(HERE, "kami_gender.txt")

FEMALE, MALE, UNKNOWN = "Q6581072", "Q6581097", "Q24238356"

# Obvious markers only (Emma: "only the obvious cases").
FEMALE_MARKERS = ("姫", "媛", "比売", "比咩", "毘売", "日売", "比女", "日女", "女神", "皇女", "夫人",
                  "吉祥女", "ヒメ", "トメ")
MALE_MARKERS = ("彦", "日子", "ヒコ", "之男", "男神", "男命", "男尊", "筒男", "王")


def obvious_gender(ja):
    """FEMALE / MALE when the name says so unambiguously, else None."""
    f = any(m in ja for m in FEMALE_MARKERS)
    m = any(x in ja for x in MALE_MARKERS)
    if f and not m:
        return FEMALE
    if m and not f:
        return MALE
    return None


def created_qids(path=STATE):
    with io.open(path, encoding="utf-8") as fh:
        return sorted(set(json.load(fh).values()))


def query(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    return f"""SELECT ?k ?ja ?g WHERE {{
  VALUES ?k {{ {values} }}
  ?k rdfs:label ?ja FILTER(LANG(?ja) = "ja")
  OPTIONAL {{ ?k wdt:P21 ?g }}
}}"""


def read_items(rows):
    """{qid: (ja, {P21 values})}."""
    out = {}
    for b in rows:
        q = b["k"]["value"].rsplit("/", 1)[-1]
        ja, gs = out.setdefault(q, (b["ja"]["value"], set()))
        if "g" in b:
            gs.add(b["g"]["value"].rsplit("/", 1)[-1])
    return out


def build_lines(items):
    lines = []
    for q in sorted(items):
        ja, gs = items[q]
        if gs - {UNKNOWN}:          # already has a real gender: never change it
            continue
        g = obvious_gender(ja)
        if g:
            lines.append(f"{q}|P21|{g}")
    return lines


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    items = read_items(wdqs_transport.query(query(created_qids())))
    lines = build_lines(items)
    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(items)} kami checked; wrote {len(lines)} P21 line(s) to {OUTPUT}")


if __name__ == "__main__":
    main()
