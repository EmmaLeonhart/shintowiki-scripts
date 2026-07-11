#!/usr/bin/env python3
"""
generate_souken_den_quickstatements.py
======================================
Import the *legendary* founding dates from jawiki infoboxes — the 伝-dates that
`generate_souken_quickstatements.py` deliberately refuses — as `P571` (inception)
carrying `P1480` (sourcing circumstances) = `Q18122778` (presumably).

Emma 2026-07-09, asked whether the 8,837 skipped date fields should land this way:
*"Yes — P571 + P1480 presumably."*

Both entities were verified live before anything was written: `P1480` is
"sourcing circumstances — qualification of the truth or accuracy of a source",
and its own description enumerates `presumably (Q18122778)`. Neither was recalled
from memory.

WHAT A 伝-DATE LOOKS LIKE
------------------------
    | 創建 = 伝[[大同 (日本)|大同]]2年（[[807年]]）
    | 創建 = （伝）[[天平]]元年（[[729年]]）
    | 創建 = 社伝によれば[[貞観 (日本)|貞観]]5年（[[863年]]）

The article states a specific year and simultaneously marks it as tradition
(伝 / （伝） / 社伝 / 寺伝 / 伝承). That is precisely the case `P1480 = presumably`
exists for: the source gives a value and says the value is presumed.

THIS SCRIPT IS THE COMPLEMENT OF ITS SIBLING, NOT AN EXTENSION
--------------------------------------------------------------
`generate_souken_quickstatements.parse_year()` skips a field the moment it sees
`伝`. This one *requires* `伝` and skips everything that sibling skips for any
other reason (不詳 unknown, 頃 circa, 年間 era-span, 世紀 century, 以前/以降
before/after, BC, multiple distinct years, no Gregorian year at all). The two
accept-sets are therefore disjoint by construction, and a test pins that: no
field can ever be imported twice, once clean and once presumed.

Items already carrying `P571` are skipped — a presumed date must never overwrite
or compete with a real one.

Output: `souken_den_p571.txt`, registered in `ATOMIC_FILES` so the daily editor
actually reads it (a batch written anywhere else is silently never run).

    <item>|P571|+YYYY-00-00T00:00:00Z/9|P1480|Q18122778|S143|Q177837|S4656|"<jawiki url>"
"""
import io
import os
import re
import sys
import time
import urllib.parse

import argparse

from generate_souken_quickstatements import (
    CONFIGS,
    _REBUILD,
    _VAGUE,
    embedded_titles,
    fetch_batch,
    items_with_p571,
    strip_citations,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "souken_den_p571.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

PRESUMABLY = "Q18122778"   # sourcing circumstances value
P_SOURCING = "P1480"

# The tradition markers: 伝 alone, （伝）, and the compounds 社伝 / 寺伝 / 伝承 /
# 伝説, all of which attribute the date to tradition rather than record.
_DEN_RE = re.compile(r"伝")

# Everything the sibling skips for a reason OTHER than 伝. A field carrying any of
# these is not merely presumed — it is vague, and no single year can be asserted.
_OTHER_SKIP_RE = re.compile(_VAGUE)

_YEAR_RE = re.compile(r"(\d{3,4})年")

# Fields routinely pack a founding and a rebuilding into one value, separated by a
# line break or a punctuation mark:
#     伝・奈良時代初期<br />再興：平成9年（1997年）
# The only Gregorian year there belongs to the 再興, and the traditional founding has
# none at all. Taking "the single year in the field" imported 1997 as 竹林寺's
# inception. So the year must come from the segment that actually carries the 伝.
_SEGMENT_RE = re.compile(r"<br\s*/?>|[\n；;、,]")


_REBUILD_RE = re.compile(_REBUILD)


def _years_in(text):
    return {y for y in (int(m) for m in _YEAR_RE.findall(text)) if 300 <= y <= 2026}


def parse_den_year(field):
    """The single unambiguous Gregorian year of a *traditional* date, or None.

    The year is read only from the 伝-bearing segment(s). A segment WITHOUT 伝 that
    still carries a year is fatal unless it is explicitly a rebuilding — otherwise
    `伝807年、810年` (two rival traditional years) would silently resolve to 807.
    """
    field = strip_citations(field)
    if not field.strip():
        return None
    if not _DEN_RE.search(field):
        return None                      # not a traditional date — sibling's job
    if _OTHER_SKIP_RE.search(field):
        return None                      # vague as well as traditional

    years = set()
    for segment in _SEGMENT_RE.split(field):
        if _DEN_RE.search(segment):
            years |= _years_in(segment)
        elif _years_in(segment) and not _REBUILD_RE.search(segment):
            return None                  # a rival year we cannot attribute
    if len(years) != 1:
        return None
    return years.pop()


def qs_line(qid, year, url):
    return '{}|P571|+{:04d}-00-00T00:00:00Z/9|{}|{}|S143|Q177837|S4656|"{}"'.format(
        qid, year, P_SOURCING, PRESUMABLY, url)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = items_with_p571()
    print("{} shrines/temples already carry P571 (a presumed date never competes "
          "with a real one)".format(len(have)))

    lines = []
    for template, field_pat in CONFIGS:
        pat = re.compile(field_pat)
        titles = embedded_titles(template)
        if args.limit:
            titles = titles[:args.limit]
        den = not_den = no_qid = already = 0
        for i in range(0, len(titles), 50):
            for title, qid, text in fetch_batch(titles[i:i + 50]):
                m = pat.search(text or "")
                if not m:
                    continue
                year = parse_den_year(m.group(1))
                if year is None:
                    not_den += 1
                    continue
                if not qid:
                    no_qid += 1
                    continue
                if qid in have:
                    already += 1
                    continue
                url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(
                    title.replace(" ", "_"))
                lines.append(qs_line(qid, year, url))
                den += 1
            time.sleep(0.3)
        print("{}: {} articles, traditional-year={}, not-a-clean-伝-date={}, "
              "no-QID={}, already-had-P571={}".format(
                  template, len(titles), den, not_den, no_qid, already))

    lines = sorted(set(lines))
    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print("{} presumed-P571 lines -> {}".format(len(lines), OUTPUT))


if __name__ == "__main__":
    main()
