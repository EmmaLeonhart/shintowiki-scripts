#!/usr/bin/env python3
"""Caution gate for the Wikidata drip while ブルーノ・プラス is active.

Emma 2026-07-10, after reading `docs/bruno_plus_analysis_2026-07.md`:

    "First of all, I think that we should have a one-week-long pause. … I want to
    have the freshness constraint of no editing until something hasn't been edited
    by other users for a week. … We will only run edits a week after they have
    stopped editing, or for August, that is to say, a week into August. If they
    have still been editing, then our pipeline will start. This is maximum caution
    with this person … I think that this person is an LTA."

Two independent gates, both enforced by `direct_daily_edits`, which is the single
path by which anything reaches Wikidata:

1. **Global pause** — `should_run()`. The drip is off until *seven days after the
   watched editor's most recent edit*, and never before the one-week floor
   (2026-07-17). While they keep editing, the pause keeps extending.

   The **hard cap** (2026-08-08, "a week into August") is load-bearing: without it
   an editor who never stops would block our pipeline for ever, and the gate would
   have handed them a veto. On that date the drip resumes regardless.

2. **Per-item freshness** — `is_item_fresh_enough()`. Never touch an item that any
   *other* user edited within the last seven days. This one is not about a person;
   it is a permanent, general rule that dodges every future contributor and removes
   the whole class of edit conflict. It stays after the global pause lifts.

Nothing here removes data, contacts anyone, or reverts anything. Emma: *document,
don't touch*; *no contact, stay invisible*.
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

WATCHED_USER = "ブルーノ・プラス"

# The one-week pause Emma asked for, measured from the day the policy was set.
MIN_PAUSE_UNTIL = datetime.date(2026, 7, 17)

# "or for August, that is to say, a week into August. If they have still been
# editing, then our pipeline will start."
HARD_RESUME = datetime.date(2026, 8, 8)

# Both gates use the same window.
QUIET_DAYS = 7

# Emma 2026-07-10. The danger is not this editor's throughput; it is that an LTA
# draws attention, and attention lands on whoever is editing nearby. Attention is a
# STRONGER signal than their edit rate, so every rule below overrides HARD_RESUME —
# that cap exists only to stop a busy editor holding a permanent veto over us, not
# to force us to edit through a live dispute.
#
# Three distinct signals, deliberately NOT collapsed into one:
#
#   1. jawiki 井戸端 (the Japanese project chat) — an INDEFINITE hold on the mere
#      presence of their name. Emma: "due to the nature of the Japanese Wikipedia
#      Project Chat … it has a 90-day expiration on conversations in it … Also,
#      because it has a tendency to necro a bit more. If this person's name, the
#      text of their name, is ever present in Japanese Wikipedia Project Chat, then
#      we put it on hold. Just no edits." A dated pause is wrong here: the thread
#      can lie dormant and be revived, so the hold lasts as long as the name is on
#      the page.
#
#   2. Their talk page — 30 days from the LAST ACTIVITY, not from a mention.
#      "If there has been any activity within a month on their talk page, then there
#      will be a month of no edits."
#
#   3. Administrators' noticeboards (and the other discussion venues) — 30 days from
#      a mention. "If there has been a mention of them on the administrators' notice
#      board within the last month, then no editing."
#
# Emma on the worst case, which she accepts: "the worst-case scenario in the safe one
# is that we have not been editing for an extended period, and then they get blocked
# … and then a month later our pipeline starts again."
ATTENTION_PAUSE_DAYS = 30

# Accounts whose edits are OURS and therefore never make an item "fresh".
# Everything reaching Wikidata goes out under Emma's account.
OUR_ACCOUNTS = {"Immanuelle", "EmmaBot"}

WD_API = "https://www.wikidata.org/w/api.php"
UA = USER_AGENT


# ─────────────────────────── pure logic (tested offline) ───────────────────────────

def routine_resume(last_watched_edit):
    """Seven quiet days after their last edit, floored and capped."""
    if last_watched_edit is None:
        return MIN_PAUSE_UNTIL
    quiet = last_watched_edit + datetime.timedelta(days=QUIET_DAYS)
    return min(max(MIN_PAUSE_UNTIL, quiet), HARD_RESUME)


def resume_date(last_watched_edit, talk_activity=None, noticeboard_mention=None,
                project_chat_hold=False):
    """The first day the drip may run, or **None meaning indefinitely held**.

    `project_chat_hold` is True while their name appears in jawiki 井戸端. There is
    no date at which that expires by itself; the hold lifts when the name leaves the
    page (archived or removed), and the next watcher run sees it gone.
    """
    if project_chat_hold:
        return None
    candidates = [routine_resume(last_watched_edit)]
    pause = datetime.timedelta(days=ATTENTION_PAUSE_DAYS)
    if talk_activity is not None:
        candidates.append(talk_activity + pause)
    if noticeboard_mention is not None:
        candidates.append(noticeboard_mention + pause)
    return max(candidates)


def should_run(today, last_watched_edit, talk_activity=None,
               noticeboard_mention=None, project_chat_hold=False):
    """May the drip run on `today`?"""
    resume = resume_date(last_watched_edit, talk_activity, noticeboard_mention,
                         project_chat_hold)
    return resume is not None and today >= resume


def pause_reason(today, last_watched_edit, talk_activity=None,
                 noticeboard_mention=None, project_chat_hold=False):
    """A one-line explanation, or None when the drip may run."""
    if project_chat_hold:
        return ("HELD INDEFINITELY: {} is named in jawiki 井戸端 (project chat). "
                "No edits until the name leaves that page.".format(WATCHED_USER))
    if should_run(today, last_watched_edit, talk_activity, noticeboard_mention):
        return None
    resume = resume_date(last_watched_edit, talk_activity, noticeboard_mention)
    pause = datetime.timedelta(days=ATTENTION_PAUSE_DAYS)

    if noticeboard_mention is not None and resume == noticeboard_mention + pause:
        return ("paused until {}: {} was mentioned at an administrators' noticeboard "
                "on {} — {}-day attention pause".format(
                    resume, WATCHED_USER, noticeboard_mention, ATTENTION_PAUSE_DAYS))
    if talk_activity is not None and resume == talk_activity + pause:
        return ("paused until {}: activity on {}'s talk page on {} — {}-day "
                "attention pause".format(resume, WATCHED_USER, talk_activity,
                                         ATTENTION_PAUSE_DAYS))
    if last_watched_edit is None:
        return "paused until {} (one-week floor)".format(resume)
    return ("paused until {}: {} last edited {} and the quiet window is {} days "
            "(hard cap {})".format(resume, WATCHED_USER, last_watched_edit,
                                   QUIET_DAYS, HARD_RESUME))


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


def fetch_last_watched_edit(user=WATCHED_USER):
    """Date of the watched user's most recent edit, or None."""
    d = _api({"action": "query", "list": "usercontribs", "ucuser": user,
              "uclimit": 1, "ucprop": "timestamp"})
    rows = d.get("query", {}).get("usercontribs", [])
    return _to_date(rows[0]["timestamp"]) if rows else None


def fetch_item_revisions(qid, limit=20):
    """[(user, date), …] for an item's most recent revisions."""
    d = _api({"action": "query", "prop": "revisions", "titles": qid,
              "rvprop": "timestamp|user", "rvlimit": limit, "formatversion": 2})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return []
    return [(r["user"], _to_date(r["timestamp"])) for r in pages[0].get("revisions", [])]


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    last = fetch_last_watched_edit()
    print("today (UTC):           {}".format(today))
    print("{} last edit: {}".format(WATCHED_USER, last))
    print("drip resumes on:       {}".format(resume_date(last)))
    print("hard cap:              {}".format(HARD_RESUME))
    reason = pause_reason(today, last)
    print("\n{}".format(reason if reason else "RUNNING — the gate is open."))
    return 0 if reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
