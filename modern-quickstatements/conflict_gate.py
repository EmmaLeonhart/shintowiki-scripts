#!/usr/bin/env python3
"""Per-item freshness gate for the Wikidata drip.

**The person-specific caution gate was REMOVED on 2026-07-21 (Emma's call).**
The 2026-07-10 policy paused the whole drip around one watched editor
(ブルーノ・プラス) — a global pause, plus indefinite holds on project-chat /
talk-page / noticeboard attention. Emma, 2026-07-21:

    "I'm just making a judgement call on him. I feel like he's made a couple
    edits, but he's not the threat that we think he is, so we probably don't
    actually need that filter around with him. I think that I thought we did,
    but we didn't."

So the global pause, the watched user, the hard-resume date, and the three
attention signals are all gone. `docs/bruno_plus_analysis_2026-07.md` stays as
the historical record of why they existed.

**What survives, deliberately:** the per-item freshness rule below. It was never
about a person — Emma, 2026-07-10: *"I want to have the freshness constraint of
no editing until something hasn't been edited by other users for a week."* It is
a permanent, general courtesy rule that keeps the drip off any item another
human touched recently, and it removes the whole class of edit conflict with any
contributor. Callers fail closed on lookup failure: not knowing means declining.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import datetime
import json
import urllib.parse
import urllib.request

# Never edit an item another user touched inside this window.
QUIET_DAYS = 7

# Accounts whose edits are OURS and therefore never make an item "fresh".
# Everything reaching Wikidata goes out under Emma's account. Without this the
# drip would deadlock itself after its first edit to any item.
OUR_ACCOUNTS = {"Immanuelle", "EmmaBot"}

WD_API = "https://www.wikidata.org/w/api.php"
UA = USER_AGENT


# ─────────────────────────── pure logic (tested offline) ───────────────────────────

def is_item_fresh_enough(revisions, today, our_accounts=OUR_ACCOUNTS,
                         quiet_days=QUIET_DAYS):
    """False when another user edited the item inside the quiet window.

    `revisions` is a list of `(user, date)`. Our own accounts are ignored — the
    drip must not block itself.
    """
    cutoff = today - datetime.timedelta(days=quiet_days)
    for user, when in revisions:
        if user in our_accounts:
            continue
        if when > cutoff:
            return False
    return True


def blocking_editor(revisions, today, our_accounts=OUR_ACCOUNTS,
                    quiet_days=QUIET_DAYS):
    """The most recent foreign editor inside the window, for the log line."""
    cutoff = today - datetime.timedelta(days=quiet_days)
    recent = [(w, u) for u, w in revisions if u not in our_accounts and w > cutoff]
    if not recent:
        return None
    when, user = max(recent)
    return user, when


# ─────────────────────────── live lookups ───────────────────────────

def _api(params):
    params = dict(params, format="json")
    url = WD_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _to_date(timestamp):
    return datetime.date(int(timestamp[0:4]), int(timestamp[5:7]), int(timestamp[8:10]))


def fetch_item_revisions(qid, limit=20):
    """[(user, date), …] for an item's most recent revisions."""
    d = _api({"action": "query", "prop": "revisions", "titles": qid,
              "rvprop": "timestamp|user", "rvlimit": limit, "formatversion": 2})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return []
    return [(r["user"], _to_date(r["timestamp"])) for r in pages[0].get("revisions", [])]


def main():
    print("Per-item freshness gate: quiet window {} days, our accounts {}."
          .format(QUIET_DAYS, sorted(OUR_ACCOUNTS)))
    print("The person-specific global pause was removed 2026-07-21 (Emma's call).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
