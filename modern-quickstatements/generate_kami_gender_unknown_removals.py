#!/usr/bin/env python3
"""
generate_kami_gender_unknown_removals.py
========================================
Step 2 of setting the obvious gender on the kami we created: the REMOVE generator.

Step 1 (`generate_kami_gender.py`) adds P21 = female / male where the name is obvious. This
removes the old `P21 = unknown` (Q24238356) from those kami, but ONLY where a fresh SPARQL query
confirms the item already carries P21 = female or male, so under the drip's random order the
remove can never come first (CLAUDE.md: add first, remove later, two scripts). Empty until the
step-1 lines land; that is the design.

The removal is a value-matched whole-statement removal of `P21 = Q24238356`, which
QuickStatements expresses correctly. It is not a qualifier removal.

One SPARQL query per run. GENERATOR ONLY: writes `kami_gender_unknown_removals.txt`
(ATOMIC_FILES).
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import io
import os
import sys

import wdqs_transport
from generate_kami_gender import FEMALE, MALE, UNKNOWN, created_qids

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "kami_gender_unknown_removals.txt")


def query(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    return f"""SELECT DISTINCT ?k WHERE {{
  VALUES ?k {{ {values} }}
  ?k wdt:P21 wd:{UNKNOWN} .
  # THE CONFIRMATION: the real gender has already landed.
  ?k wdt:P21 ?real . FILTER(?real IN (wd:{FEMALE}, wd:{MALE}))
}}"""


def build_lines(qids):
    return sorted({f"-{q}|P21|{UNKNOWN}" for q in qids})


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = wdqs_transport.query(query(created_qids()))
    lines = build_lines(b["k"]["value"].rsplit("/", 1)[-1] for b in rows)
    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} confirmed removal line(s) (0 is normal until step 1 has landed)")


if __name__ == "__main__":
    main()
