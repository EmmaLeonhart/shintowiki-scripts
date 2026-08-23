#!/usr/bin/env python3
"""
remove_wikidata_crud_categories.py
==================================
Step 2 of the "wikidata-missing" crud lifecycle (Emma 2026-05-30). ~6 months
after `add_wikidata_crud_categories.py` made `[[Category:Pages without wikidata]]`
and `[[Category:Categories missing wikidata]]` crud (to drain legacy literal
tags), un-crud them so they go back to being normal maintenance categories that
the self-categorizing {{wikidata link}} template keeps populated.

Removes the `[[Category:Crud categories]]` tag from each target. Date-gated: a
no-op until REMOVE_DATE. Idempotent. Two separate scripts, add-first remove-later
(never one).
"""

import argparse
import datetime
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.user_agent import USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5
# hand-built agent, not the canonical one -- so it never matched the allowlisted string.
# was: UA = ("ShintoWikiBot/1.0 (https://github.com/EmmaLeonhart/shintowiki-scripts; " f"{contact('wikidata')})")
UA = USER_AGENT

REMOVE_DATE = datetime.date(2026, 12, 6)  # ~6 months after the crud-add
TARGETS = ["Category:Pages without wikidata", "Category:Categories missing wikidata"]
CRUD_RE = re.compile(r"\n?\[\[\s*Category\s*:\s*Crud categories\s*\]\]\s*", re.IGNORECASE)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually save (default dry-run).")
    ap.add_argument("--max-edits", type=int, default=10)
    ap.add_argument("--run-tag", required=True)
    args = ap.parse_args()

    today = datetime.datetime.utcnow().date()
    if today < REMOVE_DATE:
        print(f"Before REMOVE_DATE ({REMOVE_DATE.isoformat()}); no-op (today {today.isoformat()}).")
        return 0

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=UA)
    if not PASSWORD:
        print("No WIKI_PASSWORD — read-only (dry-run only).")
    else:
        login_with_retry(site, USERNAME, PASSWORD)
        print(f"Logged in as {USERNAME}")

    edits = 0
    for title in TARGETS:
        if edits >= args.max_edits:
            break
        page = site.pages[title]
        if not page.exists:
            print(f"SKIP {title} (missing)")
            continue
        text = page.text()
        if not CRUD_RE.search(text):
            print(f"SKIP {title} (not crud)")
            continue
        new_text = CRUD_RE.sub("\n", text).rstrip() + "\n"
        if not args.apply:
            print(f"[DRY] un-crud {title}")
            edits += 1
            continue
        page.save(new_text, summary=f"Bot: un-crud wikidata-missing category "
                                    f"(legacy literal tags drained) {args.run_tag}")
        edits += 1
        print(f"EDIT {title} (removed crud tag)")
        time.sleep(THROTTLE)

    print(f"\nDone. Edits: {edits}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
