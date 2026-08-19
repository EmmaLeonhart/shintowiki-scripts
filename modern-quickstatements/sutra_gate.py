#!/usr/bin/env python3
"""Timed gate for the Sutra / Emma-profile drip.

Emma 2026-07-16:

    "I don't think it's going to be that difficult. I think you should actually run
    this autonomously. It's pretty easy. All you need to do is make a thing in the
    Shinto Wiki scripts that, two weeks from now, checks if it exists. If it does
    exist, then it starts a thing of a daily one edit to the entry or one of the
    quick statements being run by an autonomous thing that occurs at a random point
    in our edit scheme. This is actually something that very much can be done
    autonomously, and saying that it can't be done autonomously is being
    unproductive for no reason!"

She is right, and this is the whole implementation. Two gates:

1. **The wait** — nothing until `START_DATE` (2 weeks from 2026-07-16). This is the
   deliberate pause in `sutra-page-plan.md`: leave the S2 item alone, let it settle,
   then drip content in.

2. **"#if this one is unmolested"** — her own line in the QS source. The Sutra item
   must still EXIST and not have been merged away during the wait. If someone deleted
   or redirected it, the rename trick is off and the batch must not run.

Then `sutra_profile.txt` drips at **one line per day** (FILE_DAILY_CAPS in
direct_daily_edits.py) through the existing random 30-90s scheduler — i.e. "a random
point in our edit scheme", using the machinery that already exists rather than a new one.

Fails CLOSED: any error -> gate shut. The global conflict_gate still applies on top;
this is an extra gate, never a bypass.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
from shinto_miraheze.wd_pace import wd_pace

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "shinto_miraheze")):
    _root = os.path.dirname(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
# Imported unconditionally on purpose. This used to sit in a try/except whose handler was
#         WIKIDATA_USER_AGENT = <a non-canonical hand-built agent>
# marked `pragma: no cover`. That is a silent fail-OPEN in a system whose whole design is
# fail-closed: any import hiccup would quietly put the wrong domain on Wikidata
# requests, untested and invisible. An unimportable agent must stop the run instead.
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

# Emma said this 2026-07-16, "two weeks from now".
START_DATE = datetime.date(2026, 7, 30)

# The S2 -> Sutra item. Her QS is explicitly gated "#if this one is unmolested".
WATCHED_ITEM = "Q140570154"

WD_API = "https://www.wikidata.org/w/api.php"


def _exists_and_unmolested(qid=WATCHED_ITEM):
    """True only if qid is a LIVE item — not missing, not merged away.

    redirects=no is load-bearing: wbgetentities silently FOLLOWS redirects and
    returns the target's data under the requested id, so without it a merged-away
    item reads as alive. That exact trap produced a retracted phantom-duplicate
    report in funding-and-networking on 2026-07-16.
    """
    url = WD_API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": qid, "redirects": "no",
        "props": "info", "format": "json",
    })
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    wd_pace()
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if "error" in d:
        raise RuntimeError(f"API error for {qid}: {d['error'].get('code')}")
    entities = d.get("entities")
    # An absent `entities`, or a qid the API declined to return, must NOT read as
    # "alive" — `"missing" not in {}` is True, which would fail OPEN. Require the
    # entity to be positively present and not flagged missing.
    if not entities or qid not in entities:
        raise RuntimeError(f"{qid} absent from the API response")
    ent = entities[qid]
    return "missing" not in ent and bool(ent.get("id"))


def is_open(today=None):
    """(open?, reason) — may the Sutra drip run at all right now?"""
    today = today or datetime.date.today()
    if today < START_DATE:
        return False, f"waiting until {START_DATE} (Emma's 2-week settle; {(START_DATE - today).days}d left)"
    try:
        if not _exists_and_unmolested():
            return False, f"{WATCHED_ITEM} is gone/merged — 'molested', so the batch is off"
    except Exception as exc:
        return False, f"existence check failed ({exc}) — failing CLOSED"
    return True, f"open: past {START_DATE} and {WATCHED_ITEM} is live"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"sutra drip {'OPEN' if ok else 'CLOSED'}: {why}")
