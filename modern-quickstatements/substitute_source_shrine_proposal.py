#!/usr/bin/env python3
"""
substitute_source_shrine_proposal.py
====================================
ONE-SHOT, date-gated Wikidata talk-page edit (Emma 2026-06-16).

On/after FIRE_DATE, replace the live transclusion

    {{Wikidata:Property proposal/Source Shrine}}

on [[Wikidata talk:WikiProject Shinto]] with

    {{subst:Wikidata:Property proposal/Source Shrine}} transcluding finished proposal~~~~

i.e. subst the (now-finished) property-proposal template into the page so the
proposal is permanently archived inline, sign it, and leave the trailing note.
Edit summary is exactly "substituting finished proposal".

THIS IS THE SANCTIONED EXCEPTION to the "Wikidata is edited only via the
QuickStatements pipeline" rule (CLAUDE.md). That rule governs *item data*
(claims/qualifiers/labels/references), which QuickStatements cannot apply to a
talk page anyway. Emma explicitly authorised this single talk-page wikitext
edit on 2026-06-16 as an exception. Do NOT generalise this into a bespoke
Wikidata data editor.

Behaviour:
* Date-gated: a no-op until FIRE_DATE, so it can be wired into a scheduled
  workflow now and simply starts acting on that date.
* Idempotent: only acts if the un-subst'd template string is still present.
  After the subst lands, the server expands the template, the marker is gone,
  and every later run is a no-op.
* "Pull from remote" is satisfied by fetching the live page text immediately
  before editing.

Auth: Wikidata bot-password via MW_BOTNAME / BOT_TOKEN (same secrets as
direct_daily_edits.py).

Standard flags: --apply (default dry-run), --max-edits, --run-tag. The run-tag
is intentionally NOT written into the edit summary — Emma specified the summary
verbatim, and a github run-link in a Wikidata talk-page summary would be
conspicuous bot editing.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wikidata_edit_allowed import editing_allowed as wikidata_editing_allowed
import argparse
import datetime
import io
import os
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WD_API = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT

FIRE_DATE = datetime.date(2026, 9, 4)  # 80 days after 2026-06-16

PAGE_TITLE = "Wikidata talk:WikiProject Shinto"
OLD = "{{Wikidata:Property proposal/Source Shrine}}"
NEW = "{{subst:Wikidata:Property proposal/Source Shrine}} transcluding finished proposal~~~~"
SUMMARY = "substituting finished proposal"


def wd_login():
    """Log in to Wikidata and return (session, csrf_token), or (None, None)."""
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        missing = [n for n, v in (("MW_BOTNAME", user), ("BOT_TOKEN", password)) if not v]
        print(f"No creds ({', '.join(missing)} not set) — read-only / dry-run only.")
        return None, None

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]

    r = session.post(WD_API, data={
        "action": "login", "lgname": user, "lgpassword": password,
        "lgtoken": login_token, "format": "json",
    }, timeout=60)
    r.raise_for_status()
    if r.json().get("login", {}).get("result") != "Success":
        print(f"Login failed: {r.json()}")
        return None, None
    print(f"Logged in as {r.json()['login']['lgusername']}")

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    return session, r.json()["query"]["tokens"]["csrftoken"]


def fetch_page_text(session):
    """Fetch the live wikitext of PAGE_TITLE (None if missing)."""
    s = session or requests.Session()
    if session is None:
        s.headers.update({"User-Agent": UA})
    r = s.get(WD_API, params={
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "titles": PAGE_TITLE, "format": "json", "formatversion": "2",
    }, timeout=60)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    return pages[0]["revisions"][0]["slots"]["main"]["content"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually save (default dry-run).")
    ap.add_argument("--max-edits", type=int, default=1)
    ap.add_argument("--run-tag", default="(manual)",
                    help="CI run tag (accepted for template parity; not written to summary).")
    args = ap.parse_args()

    # GATE 0 - THE WIKIDATA LOCKOUT. Emma, 2026-08-18: "I want a gate to be set up
    # that there will be no wikidata editing for a month." Single source of truth:
    # shinto_miraheze/wikidata_editing_lockout.state. It is checked here, in code,
    # rather than only in the workflow, so a local or manual run is covered too. A
    # locked run is a SKIP, not a failure: nothing was attempted, so nothing broke.
    wd_ok, wd_why = wikidata_editing_allowed()
    if not wd_ok:
        print("SKIPPED: wikidata lockout - {}".format(wd_why))
        return 0


    today = datetime.datetime.utcnow().date()
    if today < FIRE_DATE:
        print(f"Before FIRE_DATE ({FIRE_DATE.isoformat()}); no-op (today {today.isoformat()}).")
        return 0

    session, csrf = wd_login()

    text = fetch_page_text(session)
    if text is None:
        print(f"Page [[{PAGE_TITLE}]] does not exist — nothing to do.")
        return 0

    if OLD not in text:
        print("Marker template not present (already substituted or removed) — no-op.")
        return 0

    new_text = text.replace(OLD, NEW)
    print(f"Will replace {text.count(OLD)} occurrence(s) of the un-subst'd template.")

    if not args.apply:
        print("[DRY] would save the substitution edit. Re-run with --apply to perform it.")
        return 0

    if not session or not csrf:
        print("No write credentials — cannot apply. (Run in CI with MW_BOTNAME/BOT_TOKEN.)")
        return 1

    r = session.post(WD_API, data={
        "action": "edit", "title": PAGE_TITLE, "text": new_text,
        "summary": SUMMARY, "bot": 1, "token": csrf, "format": "json",
    }, timeout=60)
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        print(f"Edit failed: {result['error'].get('info', result['error'])}")
        return 1
    print(f"EDIT saved: {result.get('edit', {}).get('result')} (summary: {SUMMARY!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
