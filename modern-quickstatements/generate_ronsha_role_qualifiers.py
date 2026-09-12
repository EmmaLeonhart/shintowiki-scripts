#!/usr/bin/env python3
"""
generate_ronsha_role_qualifiers.py
==================================
Add the missing ``P2868`` role qualifier to ``P460`` statements on Shikinai Ronsha
items. **Qualifier-only** — it never restates or alters the ``P460`` value.

## Why this exists

The 2026-09-12 conformity re-measurement
(`docs/wikidata_model_adoption_review_2026-07-28.md`) found this figure frozen:

    ronsha P460 statements carrying P2868 :  1,613 of 2,058   2026-07-28
                                             1,613 of 2,058   2026-09-12

Identical, to the statement, six weeks apart — because `grep -c "|P2868|"` across
every atomic file in this directory returns **zero**. The other two flat numbers
in that table are drip-limited rather than stalled: `P361`/`P1545` have 5,069 +
2,115 + 793 + 57 lines queued against them. This one had nothing at all.

## The value is read off the item's own type, not off a frequency

Of the 1,613 statements that already carry the qualifier, **1,611 use
``Q135022904`` (Shikinai Ronsha)** — the same QID as the item's own ``P31`` — and
2 use ``Q135026601`` (Shikinai Hiteisha). Those two are a different claim
(*denied*, not *disputed*) sitting on items typed Ronsha, which is an
inconsistency in existing data and not a pattern to copy.

So the emitted role is not a majority vote. For an item typed Ronsha, the role
restates what its own ``P31`` already says. CLAUDE.md, on the ``n/a`` vs ``0``
lesson: measure what a value MEANS, not how often it occurs.

## ⛔ The guard, which is not optional

``P31`` is not exclusive. `generate_ronsha_ojp_name_removals.py` documents it:
items typed BOTH ``Q135022904`` (Ronsha) and ``Q135038714`` (Disputed Shikinaisha
/ Shikigeisha) are Engishiki *entries* that also carry the Ronsha class, and they
are a different thing from a pure candidate. ``Q134917286`` (Shikinaisha) is the
same case. This script emits only for **pure** Ronsha, exactly as that one does —
the guard is inherited, not invented here.

Statements already carrying ANY ``P2868`` are skipped, the two Hiteisha included.
Nothing is overwritten.

## Shape

    Qxxx|P460|Qyyy|P2868|Q135022904

`direct_daily_edits.execute_line` finds the existing claim by value and attaches
the qualifier to it. Re-running is a no-op once the qualifier is there, so the
file drains and goes inert — the same re-derive-from-live-state design as the
other backfills here.

GENERATOR ONLY. It writes a `.txt`; it never edits Wikidata, and the lines carry
no edit summaries (CLAUDE.md, "Wikidata editing — ONE path only").

Output: ``ronsha_role_qualifiers.txt``
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
import urllib.parse
import urllib.request

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

WDQS = "https://query-main.wikidata.org/sparql"
# The repo floor for WDQS (CLAUDE.md). One query here, but the interval is not a
# per-script choice.
WDQS_THROTTLE = 2.5

RONSHA = "Q135022904"          # Shikinai Ronsha — the class AND the role value
SHIKINAISHA = "Q134917286"     # a real Engishiki shrine; not a candidate
DISPUTED = "Q135038714"        # Disputed Shikinaisha / Shikigeisha — an ENTRY

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "ronsha_role_qualifiers.txt")

QUERY = f"""
SELECT DISTINCT ?s ?v WHERE {{
  ?s wdt:P31 wd:{RONSHA} ; p:P460 ?st .
  ?st ps:P460 ?v .
  FILTER NOT EXISTS {{ ?st pq:P2868 ?any }}
  FILTER NOT EXISTS {{ ?s wdt:P31 wd:{SHIKINAISHA} }}
  FILTER NOT EXISTS {{ ?s wdt:P31 wd:{DISPUTED} }}
}}
"""


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
            # Repo policy: bail, never retry.
            raise SystemExit("429 from WDQS — bailing.")
        raise


def build_lines(bindings):
    """One qualifier-only line per (item, P460 value). Deduplicated and sorted so
    the file is stable between runs and its diff is readable."""
    out = set()
    for b in bindings:
        s = b["s"]["value"].rsplit("/", 1)[-1]
        v = b["v"]["value"].rsplit("/", 1)[-1]
        if not s.startswith("Q") or not v.startswith("Q"):
            continue
        out.add(f"{s}|P460|{v}|P2868|{RONSHA}")
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the count and a sample; write nothing")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Querying WDQS for pure Ronsha whose P460 carries no P2868…")
    lines = build_lines(wdqs(QUERY))
    print(f"{len(lines)} qualifier-only lines")
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
