#!/usr/bin/env python3
"""~1AM daily check: did EmmaBot edit shinto.miraheze.org in the past 8 hours?

Emma 2026-07-11: after a full day of Miraheze 403 anti-DDoS challenges (no
EmmaBot edit landed 03:44-23:xx UTC), the plan is a hard week-long editing
lockout that engages automatically. This is the checker that engages it.

Logic (deliberately literal, per Emma's spec):

  * If a lockout is ALREADY in force (today < locked_until): leave it untouched.
    We do NOT re-extend it — a locked week means EmmaBot makes zero edits, so a
    naive "no edits -> lock" would perpetually re-lock. The lockout expires on
    its own date and editing resumes; the next check then re-evaluates cleanly.
  * Otherwise, query EmmaBot's contributions over the past 8 hours:
      - >= 1 edit  -> editing is healthy; write locked=false ("continues on").
      - 0 edits    -> "gated for this week": write locked=true with
                      locked_until = today + 7 days.
    Reaching the API is itself part of the test: if the anti-DDoS 403 (or any
    error) blocks the read, we cannot see any edits, so it counts as 0 edits
    and the lockout engages. Fail-closed is correct — if we cannot even READ,
    we certainly cannot edit.

The state file is consumed by wiki_edit_allowed.py, which every wiki-writing
workflow calls as a bail-early guard.

    python wiki_editing_lockout_check.py            # dry-run: print verdict, no write
    python wiki_editing_lockout_check.py --apply    # write the state file
"""
import argparse
import datetime
import io
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

STATE_PATH = pathlib.Path(__file__).with_name("wiki_editing_lockout.state")
API = "https://shinto.miraheze.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
LOCKOUT_DAYS = 7
WINDOW_HOURS = 8


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def emmabot_edits_in_window(username, hours):
    """(count, detail). count = -1 signals the API was unreachable/403 (fail-closed)."""
    start = _utcnow()
    end = start - datetime.timedelta(hours=hours)
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": username,
        "ucstart": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ucend": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uclimit": "5",
        "ucprop": "timestamp",
        "format": "json",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return -1, "403 anti-DDoS challenge — API unreadable (counts as 0 edits)"
        return -1, f"HTTP {e.code} — API unreadable (counts as 0 edits)"
    except Exception as e:
        return -1, f"unreachable: {e} (counts as 0 edits)"
    contribs = data.get("query", {}).get("usercontribs", [])
    return len(contribs), f"{len(contribs)} edit(s) by {username} in the last {hours}h"


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the state file")
    ap.add_argument("--username", default=os.environ.get("WIKI_EDIT_USERNAME", "EmmaBot"),
                    help="editing account to check (default EmmaBot / $WIKI_EDIT_USERNAME)")
    args = ap.parse_args()

    # Contributions are attributed to the base account, not the bot-password
    # login "EmmaBot@EmmaBot" that $WIKI_USERNAME may carry — strip the suffix.
    username = args.username.split("@", 1)[0] or "EmmaBot"

    now = _utcnow()
    today = now.date()
    state = load_state()

    # 1) Already locked and not yet expired -> leave untouched (no re-extend).
    locked_until = state.get("locked_until")
    if state.get("locked") and locked_until:
        try:
            until = datetime.date.fromisoformat(locked_until)
        except ValueError:
            until = None
        if until and today < until:
            print(f"Lockout already in force until {locked_until} (today {today}) — leaving untouched.")
            return 0

    # 2) Not currently locked -> evaluate the 8h edit window.
    count, detail = emmabot_edits_in_window(username, WINDOW_HOURS)
    print(detail)

    if count > 0:
        new_state = {
            "locked": False,
            "locked_until": None,
            "reason": f"{detail} at {now:%Y-%m-%dT%H:%M:%SZ} — editing healthy",
            "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        print("EmmaBot is editing — wiki editing continues (unlocked).")
    else:
        until = today + datetime.timedelta(days=LOCKOUT_DAYS)
        new_state = {
            "locked": True,
            "locked_until": until.isoformat(),
            "reason": f"no EmmaBot edits in {WINDOW_HOURS}h ({detail}) at "
                      f"{now:%Y-%m-%dT%H:%M:%SZ} — gated for the week",
            "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        print(f"NO EmmaBot edits in {WINDOW_HOURS}h — LOCKING wiki editing until {until.isoformat()}.")

    if args.apply:
        STATE_PATH.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        print(f"wrote {STATE_PATH.name}: locked={new_state['locked']} "
              f"until={new_state['locked_until']}")
    else:
        print("(dry-run — pass --apply to write the state file)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
