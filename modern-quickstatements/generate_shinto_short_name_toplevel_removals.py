#!/usr/bin/env python3
"""
generate_shinto_short_name_toplevel_removals.py
===============================================
Step 2 of moving kami short names (P1813) onto the honorific statement: the REMOVE
generator.

Emma, 2026-10-08: *"short name is supposed to be a qualifier but is being applied as
a top level statement"*, then, choosing the model: qualifier on P1035. Step 1 is
`generate_shinto_short_names.py`, which now emits

    <kami>|P1035|<honorific>|P1813|ja:"<short name>"|P1813|mul:"<romaji>"

instead of a top-level `<kami>|P1813|ja:"..."|P2440|"..."`. This removes the
top-level P1813 statements stage 2 added before that change.

⭐ **SEPARATE SCRIPT, AND REMOVE-ONLY**, per CLAUDE.md's add-first rule: a removal is
emitted only where a fresh SPARQL query confirms the same kami already carries the
SAME monolingual value as a P1813 qualifier on one of its P1035 statements. Under the
drip's random order the remove can never precede the add, so the short name is never
missing in between. The file is empty until the qualifiers land; that is the design.

The removal is a value-matched whole-statement removal of a top-level P1813 (its old
P2440 qualifier goes with it, which is intended: the romaji now lives on the P1035
statement as P1813 in `mul`). It is not a qualifier removal.

GENERATOR ONLY: writes a `.txt`, never edits Wikidata, no edit summaries.

Output: ``shinto_short_name_toplevel_removals.txt``
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import os
import sys

import wdqs_transport
from shinto_miraheze.qs_value import qs_escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "shinto_short_name_toplevel_removals.txt")

# The kami class stage 1 and stage 2 select by. Copied rather than imported:
# importing generate_shinto_honorifics rewraps stdout at import time. Kept equal to
# generate_shinto_honorifics.KAMI_CLASS by tests/test_kami_novalue_presence.py.
KAMI_CLASS = "Q524158"

QUERY = """SELECT DISTINCT ?k ?v WHERE {{
  ?k wdt:P31/wdt:P279* wd:{kami} ;
     p:P1813 ?top .
  ?top ps:P1813 ?v .
  # THE CONFIRMATION: the same value already sits as a P1813 qualifier on one of
  # this kami's P1035 statements. Without it the remove could fire first and the
  # short name would be gone with nothing holding it.
  ?k p:P1035 ?st .
  ?st pq:P1813 ?v .
}}"""


def confirmed():
    """[(kami, lang, text)] whose top-level P1813 is already a P1035 qualifier."""
    rows = wdqs_transport.query(QUERY.format(kami=KAMI_CLASS))
    out = set()
    for b in rows:
        v = b["v"]
        lang = v.get("xml:lang")
        if not lang:
            continue
        out.add((b["k"]["value"].rsplit("/", 1)[-1], lang, v["value"]))
    return sorted(out)


def build_lines(triples):
    return sorted({f'-{qid}|P1813|{lang}:"{qs_escape(text)}"' for qid, lang, text in triples})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lines = build_lines(confirmed())
    print(f"{len(lines)} confirmed removal line(s) "
          f"(0 is normal until the P1035 qualifiers have landed)")
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
