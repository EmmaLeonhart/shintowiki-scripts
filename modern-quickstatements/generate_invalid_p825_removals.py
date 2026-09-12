#!/usr/bin/env python3
"""
generate_invalid_p825_removals.py
=================================
Remove ``P825`` statements whose value is not, and cannot be, something a temple
or shrine is dedicated to.

## The rule

Emma, 2026-09-12, on ``Q1188622``: *"a completely invalid thing and we should
never add it and should universally remove it from all items it is present on."*

``P825`` is **dedicated to** — the deity a temple's main image *is*, or the kami a
shrine enshrines. ``Q1188622`` is 重要文化財, *Important Cultural Property of
Japan*: a designation the Agency for Cultural Affairs awards to an object.
"Dedicated to Important Cultural Property" is not a claim about anything.

**Universally**, per her wording: this queries every item carrying the value, not
just temples or shrines, and re-derives from live Wikidata on each run rather
than working from a frozen list. Once the statements are gone the file empties
and the batch goes inert.

## Where they came from

`generate_honzon_quickstatements.py` takes EVERY wikilink out of the jawiki
``{{日本の寺院}}`` ``本尊`` field, and temple infoboxes write the designation
beside the deity:

    |本尊 = [[阿弥陀如来]]（[[重要文化財]]）

so the designation is read as a second honzon. It was the **second most-emitted
value in `honzon_p825.txt`** — 100 of 973 lines, behind only Amitābha — and 12
had already reached Wikidata. That generator now refuses it (`INVALID_HONZON`),
and the 100 staged lines were stripped; this file is for the 12 that landed.

## Removal semantics, which are the whole risk here

A value-matched QuickStatements removal takes **every** statement on the item
with that property and value. That is exactly what is wanted — the value is
invalid, so every instance of it goes, and no correct honzon shares it. No item
is skipped for having other `P825` statements: those have different values and
are untouched, and skipping items to "protect" them is the guard-that-refuses
shape CLAUDE.md warns about.

REMOVE-ONLY, so it is drip-safe: there is no paired add that could fire first.

GENERATOR ONLY — writes a `.txt`, never edits Wikidata, no edit summaries.

Output: ``invalid_p825_removals.txt``
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

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

WDQS = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "invalid_p825_removals.txt")

# Kept as a set so a second ruling extends it without reshaping the script. Each
# entry needs Emma's word — this is a list of things she has called invalid, not
# a list of things that look wrong to a session.
INVALID_VALUES = {
    "Q1188622": "重要文化財 Important Cultural Property of Japan (Emma, 2026-09-12)",
}


def wdqs(query):
    time.sleep(WDQS_THROTTLE)
    url = WDQS + "?format=json&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": "application/sparql-results+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit("429 from WDQS — bailing.")
        raise


def holders(value):
    """Every item carrying P825 -> value, of any class."""
    rows = wdqs(f"SELECT DISTINCT ?s WHERE {{ ?s wdt:P825 wd:{value} }}")
    return sorted({b["s"]["value"].rsplit("/", 1)[-1] for b in rows})


def build_lines(value_to_items):
    out = []
    for value in sorted(value_to_items):
        for qid in value_to_items[value]:
            out.append(f"-{qid}|P825|{value}")
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    found = {}
    for value, why in sorted(INVALID_VALUES.items()):
        items = holders(value)
        found[value] = items
        print(f"{value}  {why}\n    {len(items)} item(s) carry it")

    lines = build_lines(found)
    print(f"\n{len(lines)} removal line(s)")
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
