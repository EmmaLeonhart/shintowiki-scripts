"""
generate_description_removals.py
================================
Strip every description off a named item, through the QuickStatements pipeline.

Emma, 2026-09-10, looking at `Q11558526` 浮嶋神社 / Fushima Shrine (Iyo Province)
after Wikidata's anti-abuse limiter cut her off mid-cleanup: *"This one should
have all its descriptions removed by the quickstatements."*

GENERATOR ONLY — writes QuickStatements lines into an atomic .txt file that the
single daily submitter runs. It never edits Wikidata and the lines carry no edit
summaries (CLAUDE.md "Wikidata editing — ONE path only").

## Why the item needs it

`Q11558526` is a shrine — `P31 = Q845945`, in 東温市, no sitelinks — and it
carries **41 descriptions, 40 of which say "Wikimedia disambiguation page"** in
their own language:

    sco   "Wikimedia disambiguation page"
    zh    "维基媒体消歧义页"
    uk    "сторінка значень у проєкті Вікімедіа"
    tt-latn "Mäğnälär bite Wikimedia proyektında"          … and 36 more

It has ten labels (en, eo, fi, fr, id, it, ja, pl, sl, zh-mo), so 38 of those
descriptions are ALSO orphans — a description in a language the item has no
label in, which `docs/description_label_policy.md` records as actively harmful
because the (label, description) pair is what Wikidata's uniqueness constraint
is on, and an orphan description costs a label. The one description that is
neither a dab-page string nor obviously wrong, `ru` "синтоистское святилище", is
an orphan too. Emma said all of them; all of them go.

## Why a QID list and not a query

The obvious selector — ask WDQS for shrines carrying a dab-page description —
**does not find this item.** WDQS answers `wdt:P31` for `Q11558526` correctly and
returns nothing at all for its `schema:description`, so a query-driven generator
would have been built on an index that misses the very item that prompted it.
The descriptions are read from the **Wikidata API** instead, which has them.

So the population is an explicit list. It is seeded with the one item Emma named
and nothing else — six other shrines do carry dab-page descriptions and are
listed in the DEVLOG entry for this change, but she named one.

## Self-healing

The generator re-reads each item every run and emits one line per description
that is still there, so the file empties itself as the drip lands the clears and
is regenerated to zero lines once an item is clean. Nothing needs a state file
and a re-run cannot double-clear.

A cleared description is expressed as an ordinary `Dxx` term line with an empty
value — `Q11558526|Dsco|""` — which is what QuickStatements v1 means by removing
a term, and what `wbsetdescription` with an empty `value` does. It is NOT the
`-Qxxx|...` removal syntax: `direct_daily_edits.execute_line` refuses term
removals in that form ("Term removal not supported"), and rightly, since that
path is for statements.

Output: description_removals.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

import argparse
import io
import os
import shutil
import sys
import time

import requests

WD_API = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "description_removals.txt"

# Items whose descriptions are ALL to be removed. One entry per item, with the
# reason, because "strip every description" is a big claim about an item and the
# next reader should not have to reconstruct why.
TARGETS = {
    # Emma, 2026-09-10: "This one should have all its descriptions removed by the
    # quickstatements." A shrine carrying 40 "Wikimedia disambiguation page"
    # descriptions plus one orphan ru description.
    "Q11558526": "Fushima Shrine (Iyo Province) — dab-page descriptions on a shrine",
}

THROTTLE = 1.0


def fetch_descriptions(qids):
    """{qid: {lang: value}} from the Wikidata API, 50 ids per request.

    The API, not WDQS: the query service returns no `schema:description` at all
    for Q11558526 while answering its `wdt:P31` correctly, so it cannot be
    trusted to enumerate what is actually on an item.
    """
    out = {}
    qids = sorted(qids)
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        time.sleep(THROTTLE)
        r = requests.get(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(chunk),
            "props": "descriptions", "format": "json",
        }, headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 429:
            raise SystemExit("429 from the Wikidata API — bailing "
                             "(CLAUDE.md 429 policy).")
        r.raise_for_status()
        payload = r.json()
        if "error" in payload:
            raise SystemExit(f"API error: {payload['error'].get('info')}")
        for qid, entity in payload.get("entities", {}).items():
            if "missing" in entity:
                print(f"  {qid}: MISSING on Wikidata — skipped")
                continue
            out[qid] = {lang: d["value"]
                        for lang, d in entity.get("descriptions", {}).items()}
    return out


def build_lines(descriptions):
    """One `Qxxx|Dyy|""` clear per description still present. Sorted, so the file
    is stable across runs and a rebuild is a no-op diff when nothing changed."""
    lines = []
    for qid in sorted(descriptions):
        for lang in sorted(descriptions[qid]):
            lines.append(f'{qid}|D{lang}|""')
    return lines


def publish_to_site(path):
    """Copy the batch into _site/ for the GitHub Pages browser. The file the daily
    editor reads is the bare-name one in this directory; this is only the
    published copy."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--stats", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    print("=== Remove every description from the named items ===\n")
    for qid, why in sorted(TARGETS.items()):
        print(f"  {qid}  {why}")
    print()

    descriptions = fetch_descriptions(TARGETS)
    for qid in sorted(descriptions):
        langs = sorted(descriptions[qid])
        print(f"  {qid}: {len(langs)} description(s) still present"
              + (f" — {', '.join(langs)}" if langs else " — CLEAN"))
    lines = build_lines(descriptions)

    if args.stats:
        print(f"\n--stats: {len(lines)} lines would be written")
        return

    path = args.out if os.path.dirname(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    publish_to_site(path)
    print(f"\nWrote {len(lines)} lines to {path}")


if __name__ == "__main__":
    # Rebound here rather than at import time: at module level it replaces the
    # caller's stdout, which breaks pytest's capture.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
