#!/usr/bin/env python3
"""
generate_misplaced_form_removals.py
===================================
Step 2 of the honzon image-form relocation: the REMOVE generator.

Emma, 2026-09-13, on ``Q11595955`` 秘仏 sitting as a ``P825`` value: *"hibitsu and
buddharupa are qualifiers"*, then *"qualifiers on the other thing"*. Step 1 is
`generate_honzon_quickstatements.py`, which stopped emitting them as values and now
attaches each to the deity it follows in the jawiki 本尊 field as a ``P3831``
qualifier. This removes the ones that had already landed as values.

⭐ **SEPARATE SCRIPT, AND REMOVE-ONLY**, per CLAUDE.md's add-first rule: a removal is
emitted only where a fresh SPARQL query confirms the item already carries a ``P825``
deity statement qualified ``P3831 = <that same form>``. The confirmation is in the
query, so under the drip's random order the remove can never precede the add and the
fact that the honzon is a concealed image is never lost in between.

Measured 2026-09-13: **4 statements on 3 items** —

    Q11580781  P825 -> Q11595955   (sibling deity Q11404731; also holds the
                                    Q1188622 designation invalid_p825_removals takes)
    Q11628433  P825 -> Q11595955   (sibling deity Q854773 薬師如来)
    Q85881206  P825 -> Q1000809    (sibling deity Q854773 薬師如来)

so every one has a real deity statement for the qualifier to move onto. The file is
**empty until those qualifiers land**, which is the design and not a fault — the same
shape as `katakana_reading_remove.txt`.

The removal is a whole-statement removal of a top-level ``P825``, which
QuickStatements expresses correctly. It is NOT the qualifier removal that destroyed
four ojp-hani official names on 2026-09-09 — see
`generate_kana_qualifier_remove.py`'s docstring and
`tests/test_qualifier_removal_is_refused.py`.

GENERATOR ONLY — writes a `.txt`, never edits Wikidata, no edit summaries.

Output: ``misplaced_honzon_form_removals.txt``
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import wdqs_transport
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

WDQS = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "misplaced_honzon_form_removals.txt")

# Kept in step with IMAGE_FORM_ROOTS in generate_honzon_quickstatements.py, and
# asserted equal by tests/test_honzon_image_forms.py so the two cannot drift.
FORM_ROOT = "Q1000809"     # 仏像 Buddharupa, and every subclass — 秘仏 among them

QUERY = """SELECT DISTINCT ?s ?form WHERE {{
  ?s wdt:P825 ?form .
  ?form wdt:P279* wd:{root} .
  # THE CONFIRMATION: some other P825 statement on the same item already carries
  # this form as its P3831 role. Without this the remove could fire first and the
  # article's "this image is a hibutsu" would be gone with nothing holding it.
  ?s p:P825 ?st . ?st pq:P3831 ?form .
}}"""


# The copy-pasted transport this file used to carry is now wdqs_transport.query.
# It had no retry at all, so one truncated body from WDQS ended the run — see that
# module's docstring for the incident and for why only three callers moved.
def wdqs(query):
    """Run a SPARQL query. Throttled, 429 bails, transport failures back off."""
    return wdqs_transport.query(query)


def confirmed_pairs():
    """[(item, form)] where the form is a value AND already a role qualifier."""
    rows = wdqs(QUERY.format(root=FORM_ROOT))
    return sorted({(b["s"]["value"].rsplit("/", 1)[-1],
                    b["form"]["value"].rsplit("/", 1)[-1]) for b in rows})


def build_lines(pairs):
    return sorted({f"-{qid}|P825|{form}" for qid, form in pairs})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    pairs = confirmed_pairs()
    lines = build_lines(pairs)
    print(f"{len(lines)} confirmed removal line(s) "
          f"(0 is normal until the P3831 qualifiers have landed)")
    for line in lines[:5]:
        print("   ", line)

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return

    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"\nwrote {OUTPUT}")


if __name__ == "__main__":
    main()
