#!/usr/bin/env python3
"""
generate_reisai_quickstatements.py
==================================
Import Shinto-shrine Reisai (例祭 — annual grand festival) dates from Japanese
Wikipedia into Wikidata. There is no dataset/property-populated source for these;
jawiki's `{{神社}}` infobox `例祭 =` field is the source.

Runs periodically in CI and regenerates `reisai.txt` from scratch, so as soon as
anyone adds/fixes a `例祭` on a jawiki shrine article it flows into the daily
QuickStatements pipeline and lands on Wikidata (idempotent — QS skips statements
that already exist).

Modelling (matches e.g. Q137721156 日月神社):
    <shrine> P837 <day-of-year item>          # "day in year for periodic occurrence"
             P3831 Q11385469  (qualifier)      # object has role = Reisai
             + reference citing the jawiki article
`例祭` values are parsed to a fixed month/day (`[[4月15日]]` → 4/15) and mapped to
the canonical day-of-year item via `reisai_day_qids.json` (built once from
Wikidata; 4/16 → Q2519). Edge cases — lunar (`旧暦…`), relative (`4月第2日曜日`),
festival-name-only, missing QID, or an unmapped day — are SKIPPED (counted, never
force-parsed into a wrong date).

Read-only against jawiki (no creds). Output: `reisai.txt` (an atomic file the daily
`direct_daily_edits` pipeline submits).

Usage:
    python generate_reisai_quickstatements.py            # full run
    python generate_reisai_quickstatements.py --limit 200  # sample
    python generate_reisai_quickstatements.py --stats      # print coverage, write nothing
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
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
UA = WIKIDATA_USER_AGENT
TEMPLATE = "Template:神社"
DAY_QIDS_FILE = os.path.join(HERE, "reisai_day_qids.json")
OUTPUT = os.path.join(HERE, "reisai.txt")

P_DAY = "P837"            # day in year for periodic occurrence
P_ROLE = "P3831"          # object of statement has role
Q_REISAI = "Q11385469"    # Reisai

_DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")
_REISAI_RE = re.compile(r"\|\s*例祭\s*=\s*([^\n]*)")


def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def shrine_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def parse_reisai_date(wikitext):
    """(month, day) of a fixed-gregorian 例祭, or None (no field / lunar / relative)."""
    m = _REISAI_RE.search(wikitext or "")
    if not m:
        return None
    raw = m.group(1).strip()
    if not raw or "旧暦" in raw:          # lunar -> not a gregorian day-of-year
        return None
    dm = _DATE_RE.search(raw)
    if not dm:
        return None                       # relative ("4月第2日曜日") / name-only
    month, day = int(dm.group(1)), int(dm.group(2))
    if 1 <= month <= 12 and 1 <= day <= 31:
        return month, day
    return None


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def qs_line(shrine_qid, day_qid, title):
    """P837=day-of-year, P3831=Reisai qualifier, reference = the jawiki import URL
    (P4656) — self-sufficient, so no separate 'stated in Japanese Wikipedia'."""
    url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    return f'{shrine_qid}|{P_DAY}|{day_qid}|{P_ROLE}|{Q_REISAI}|S4656|"{url}"'


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="Cap pages (0 = all).")
    ap.add_argument("--stats", action="store_true", help="Print coverage, write nothing.")
    args = ap.parse_args()

    with open(DAY_QIDS_FILE, encoding="utf-8") as f:
        day_qids = json.load(f)            # "4-16" -> "Q2519"

    titles = shrine_titles()
    if args.limit:
        titles = titles[: args.limit]

    lines, seen = [], set()
    stats = {"pages": len(titles), "no_reisai_or_edge": 0, "no_qid": 0,
             "unmapped_day": 0, "emitted": 0}
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            md = parse_reisai_date(text)
            if md is None:
                stats["no_reisai_or_edge"] += 1
                continue
            if not qid:
                stats["no_qid"] += 1
                continue
            day_qid = day_qids.get(f"{md[0]}-{md[1]}")
            if not day_qid:
                stats["unmapped_day"] += 1
                continue
            if qid in seen:
                continue
            seen.add(qid)
            lines.append(qs_line(qid, day_qid, title))
            stats["emitted"] += 1
        time.sleep(0.3)

    print(f"pages={stats['pages']} emitted={stats['emitted']} "
          f"no-reisai/edge={stats['no_reisai_or_edge']} no-qid={stats['no_qid']} "
          f"unmapped-day={stats['unmapped_day']}")
    if args.stats:
        return
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(OUTPUT)} ({len(lines)} Reisai statements)")


if __name__ == "__main__":
    main()
