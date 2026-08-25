"""Remove `part of` from modern shrines that the orphan-Shikinaisha report missed.

**What this closes.** `list_membership_removals.txt` holds 2,151 items and exists for exactly
one defect: a modern shrine carrying `P361` into a 神名帳 list, when list membership belongs to
the **entry** item and the shrine expresses its relationship as `P460 → entry` instead. But its
2,151 were selected **as ronsha**, so the population is narrower than the defect. Measuring the
149 orphan Shikinaisha against it on 2026-08-24 found **44 that meet the repo's own test for the
defect and appear in that file zero times.**

The test is the one CLAUDE.md already specifies, not a new one: *"Before calling any P361 removal
wrong, check the item for `P460`. If it points at a `Q135…`-era entry item, the item is a modern
shrine and its `P361` is the thing being removed."* These 44 point at register-era entry items and
carry `P361` into a list. They are the defect; they were simply never selected.

**Why the orphan report could not see it.** That report asks whether a Shikinaisha has a twin, so
its output is a browse table of unexplained items — 149 of them, split roughly 97 pre-existing
items to 52 register-era. "Has no twin" and "is a modern shrine wearing an entry's membership" are
different questions, and only the second one has an action attached.

**Removal is value-matched, and takes every sibling with it.** Emma, 2026-08-25: *"every single
membership thing on those items should be removed unless the membership of the Shikinaisha list is
100% accurate and is 100% what we want. We remove it and then we add it again. This is very, very
established."* So an affected item loses all of its `P361` into that list, not only the statement
that tripped the test. Re-adding correct membership is the separate later job, the same as for
`generate_multi_ordinal_removals.py`.

**One SPARQL query, then the API.** The defect shape is expressible directly, so this does not
re-derive the orphan set: it asks WDQS once for items holding both `P460 → entry` and `P361 → list`,
then reads nothing further from the query service. Paced through `wd_pace(SPARQL_INTERVAL)`, the
repo's 2.5s floor.

⛔ Generates only. Nothing is delivered before the Wikidata lockout lifts on 2026-09-18.

Usage:
    python modern-quickstatements/generate_orphan_membership_removals.py
    python modern-quickstatements/generate_orphan_membership_removals.py --dry-run
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "orphan_membership_removals.txt")
ALREADY = os.path.join(HERE, "list_membership_removals.txt")
ENDPOINT = "https://query-main.wikidata.org/sparql"

# An item that says "I am the same as <register entry>" AND separately claims to be
# part of the register's list. The P460 target is what identifies it as the modern
# shrine rather than the entry: entries do not point at entries this way.
#
# ⚠ SCOPE IS LOad-BEARING, and the first draft of this query had none. It asked only
# for `?list wdt:P31 wd:Q13406463` ("list") with no constraint on ?item at all, and
# came back with the axiom of choice, Zorn's lemma and König's theorem — it would have
# emitted P361 removals against unrelated mathematics items. Both ends are pinned now:
# the subject must be a Shinto shrine, and the list it claims must be THE SAME list its
# own P460 entry belongs to. That shared list is the whole test — it is what makes the
# membership the entry's rather than the shrine's.
#
# The second draft then over-corrected, demanding `?entry wdt:P31 wd:Q845945` and
# `?list wdt:P360 wd:Q845945` as well, and found 3 where the API found 41: register
# entries are not typed as shrines and the list items do not carry P360. An extra
# constraint that feels like tightening is a silent filter, and a query returning far
# fewer rows than a direct check is the symptom.
QUERY = """
SELECT DISTINCT ?item ?ja ?list WHERE {
  ?item wdt:P31 wd:Q845945 ;
        wdt:P460 ?entry ;
        wdt:P361 ?list .
  ?entry wdt:P361 ?list .
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
}
"""


def sparql(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    for wait in (0, 15, 45, 135):
        if wait:
            print("  backing off %ds" % wait, flush=True)
            import time
            time.sleep(wait)
        wd_pace(SPARQL_INTERVAL)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("429 from WDQS — bailing, per standing policy.")
                sys.exit(1)
            if exc.code in (503, 504):
                print("  HTTP %d from WDQS" % exc.code)
                continue
            raise
    print("WDQS kept timing out; wrote nothing.")
    sys.exit(1)


def already_staged():
    """Items the existing ronsha-selected removal file already covers."""
    staged = set()
    if not os.path.exists(ALREADY):
        return staged
    for line in io.open(ALREADY, encoding="utf-8"):
        m = re.match(r"-?(Q\d+)\|P361\|", line.strip())
        if m:
            staged.add(m.group(1))
    return staged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = sparql(QUERY)
    staged = already_staged()

    pairs, skipped, names = [], 0, {}
    for b in rows:
        item = b["item"]["value"].rsplit("/", 1)[-1]
        lst = b["list"]["value"].rsplit("/", 1)[-1]
        names[item] = b.get("ja", {}).get("value", "")
        if item in staged:
            skipped += 1
            continue
        if (item, lst) not in pairs:
            pairs.append((item, lst))

    items = sorted({i for i, _ in pairs})
    print("modern shrines holding BOTH P460 -> entry and P361 -> that entry's list: %d"
          % len({b["item"]["value"].rsplit("/", 1)[-1] for b in rows}))
    print("  already covered by list_membership_removals.txt: %d statement(s)" % skipped)
    print("  NOT covered — emitted here: %d item(s), %d (item, list) pair(s)"
          % (len(items), len(pairs)))
    for i in items[:25]:
        print("     %-14s %s" % (i, names.get(i, "")))
    if len(items) > 25:
        print("     ... and %d more" % (len(items) - 25))

    lines = ["-%s|P361|%s" % (i, l) for i, l in pairs]
    if args.dry_run:
        for ln in lines[:20]:
            print("   " + ln)
        return
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        if lines:
            fh.write("\n".join(lines) + "\n")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
