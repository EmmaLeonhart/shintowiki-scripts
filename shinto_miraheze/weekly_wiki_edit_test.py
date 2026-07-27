#!/usr/bin/env python3
"""Weekly (Sunday) test: can EmmaBot actually EDIT shinto.miraheze.org right now?

Emma 2026-07-15: rather than probe the wiki hourly/daily while it's blocked, test a
REAL edit once a week. If the edit lands, wiki editing is enabled for the week; if
it fails (the Cloudflare managed challenge blocks login, or the save errors), editing
stays locked for the week so nothing keeps hammering the 403. Works → continue;
otherwise → don't.

This REPLACES the hourly login gate + the daily 8h-contrib lockout with a single
weekly edit-test. It writes:
  * shinto_miraheze/wiki_editing_lockout.state — locked/unlocked, consumed by
    wiki_edit_allowed.py (the guard every wiki-writing workflow calls);
  * the WIKI_GATE marker + status line in queue.md (GO on pass / WAIT on fail).

On failure the lock runs 8 days (> the 7-day test cadence) so it never auto-expires
before the next Sunday test — the weekly test is the sole decider.

Needs WIKI_USERNAME (bot-password format) + WIKI_PASSWORD in the env — runs in CI.

    python weekly_wiki_edit_test.py --apply
    python weekly_wiki_edit_test.py --apply --simulate pass   # local: force outcome, no wiki
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT

import argparse
import datetime
import io
import json
import pathlib
import re

REPO = pathlib.Path(_uar)
STATE = REPO / "shinto_miraheze" / "wiki_editing_lockout.state"
QUEUE = REPO / "queue.md"
TEST_PAGE = "User:EmmaBot/edit-test"
LOCK_DAYS = 8   # > the 7-day cadence, so the lock never auto-expires before the next test


def try_edit():
    """(ok: bool, detail: str). Attempts a real edit; ok=True only if the save lands."""
    import mwclient
    user = _uos.environ.get("WIKI_USERNAME")
    password = _uos.environ.get("WIKI_PASSWORD")
    if not user or not password:
        return False, "no WIKI_USERNAME/WIKI_PASSWORD in env"
    try:
        site = mwclient.Site("shinto.miraheze.org", path="/w/", clients_useragent=USER_AGENT)
        site.login(user, password)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        page = site.pages[TEST_PAGE]
        page.save(
            f"Weekly edit-test: EmmaBot editing works as of {stamp}.\n\n"
            "This page is written once a week by weekly_wiki_edit_test.py to confirm the "
            "bot can edit; if the write fails, wiki editing is locked for the week.\n",
            summary="weekly edit-test")
        return True, f"edit landed on [[{TEST_PAGE}]] at {stamp}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def blackout_until():
    """The date before which we must not touch Miraheze AT ALL, or None.

    Emma 2026-07-27: the 403 has been up since 07-11 and never lifted, and her read
    is that our continuing to READ through it is likely why — a client that keeps
    hammering a challenge looks more malicious than one that goes quiet, so the
    challenge never gets relaxed. The fix is a genuine stretch of silence: every
    Miraheze-touching job is now gated on the lockout (reads included), and this
    probe holds off entirely until `blackout_until` passes. Without this the Sunday
    test would break the silence every 7 days and the streak would never exceed 6.

    Distinct from `locked_until`, which is always ~8 days out and is what gates the
    other workflows; using that here would suppress the probe forever. `blackout_until`
    is set once, by hand, and self-drains — once the date passes the normal weekly
    cadence resumes on its own.
    """
    if not STATE.exists():
        return None
    try:
        raw = json.loads(STATE.read_text(encoding="utf-8")).get("blackout_until")
    except Exception:
        return None
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return None


def write_state(ok, detail, now):
    # Preserve an in-force blackout across a rewrite — losing it would silently
    # restart the weekly probing that the blackout exists to stop.
    carried = {}
    bo = blackout_until()
    if bo and now.date() < bo:
        carried["blackout_until"] = bo.isoformat()
    if ok:
        st = {"locked": False, "locked_until": None,
              "reason": f"weekly edit-test PASSED — {detail}",
              "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
    else:
        until = (now.date() + datetime.timedelta(days=LOCK_DAYS)).isoformat()
        st = {"locked": True, "locked_until": until,
              "reason": f"weekly edit-test FAILED ({detail}) — locked until the next Sunday test",
              "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
    st.update(carried)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return st


def write_marker(ok, now):
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    text = QUEUE.read_text(encoding="utf-8")
    state = "GO" if ok else "WAIT"
    text = re.sub(r"<!-- WIKI_GATE: (?:GO|WAIT) -->", f"<!-- WIKI_GATE: {state} -->", text, count=1)
    if ok:
        status = (f"**Status: 🟢 GO** (weekly edit-test passed, {stamp})"
                  " — wiki editing is live for the week; work-loop, start clearing the ❓ DECISIONS.")
    else:
        status = (f"**Status: ⏸ WAITING** (weekly edit-test failed, {stamp})"
                  " — wiki editing is locked for the week. The Sunday `weekly-wiki-edit-test.yml`"
                  " job re-tests a real edit and flips this to **`WIKI_GATE: GO`** when it lands.")
    text = re.sub(r"\*\*Status: (?:🟢 GO|⏸ WAITING)\*\*[^\n]*?(?=\n)", status, text, count=1)
    QUEUE.write_text(text, encoding="utf-8")


def main():
    _usys.stdout = io.TextIOWrapper(_usys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the state file + queue marker")
    ap.add_argument("--simulate", choices=["pass", "fail"], help="skip the wiki, force the outcome (local test)")
    args = ap.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc)

    # Blackout: make NO request at all, and leave the state exactly as it is.
    bo = blackout_until()
    if bo and now.date() < bo and not args.simulate:
        print(f"BLACKOUT — no Miraheze request until {bo.isoformat()} "
              f"({(bo - now.date()).days} day(s) left). State left untouched.")
        return 1

    if args.simulate:
        ok, detail = (args.simulate == "pass"), f"simulated {args.simulate}"
    else:
        ok, detail = try_edit()
    print(("PASS — " if ok else "FAIL — ") + detail)

    if args.apply:
        st = write_state(ok, detail, now)
        write_marker(ok, now)
        print(f"wrote {STATE.name}: locked={st['locked']} until={st['locked_until']}; marker={'GO' if ok else 'WAIT'}")
    else:
        print("(dry-run — pass --apply to write state + marker)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
