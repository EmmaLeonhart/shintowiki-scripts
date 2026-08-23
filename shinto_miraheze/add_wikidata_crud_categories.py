#!/usr/bin/env python3
"""
add_wikidata_crud_categories.py
===============================
Step 1 of the "wikidata-missing" crud lifecycle (Emma 2026-05-30). Once the
self-categorizing {{wikidata link}} change has had time to propagate (a week),
make the two maintenance categories crud so `remove_crud_categories.py` strips
the LEGACY literal `[[Category:...]]` tags older runs left on member pages. The
template-emitted membership is transclusion-sourced (not a literal tag in
wikitext), so it survives — only the stale literal tags get cleaned.

Tags each target into [[Category:Crud categories]]. Date-gated: a no-op until
ADD_DATE, so it can be wired into the daily cleanup loop now and simply starts
acting on that date. Idempotent. The companion `remove_wikidata_crud_categories.py`
removes the crud designation again ~6 months out (two separate scripts, add-first
remove-later — never one).
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

ADD_DATE = datetime.date(2026, 6, 6)  # ~1 week after the 2026-05-30 template change
CRUD_TAG = "[[Category:Crud categories]]"
TARGETS = ["Category:Pages without wikidata", "Category:Categories missing wikidata"]
CRUD_RE = re.compile(r"\[\[\s*Category\s*:\s*Crud categories\s*\]\]", re.IGNORECASE)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually save (default dry-run).")
    ap.add_argument("--max-edits", type=int, default=10)
    ap.add_argument("--run-tag", required=True)
    args = ap.parse_args()

    today = datetime.datetime.utcnow().date()
    if today < ADD_DATE:
        print(f"Before ADD_DATE ({ADD_DATE.isoformat()}); no-op (today {today.isoformat()}).")
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
        text = page.text() if page.exists else ""
        if CRUD_RE.search(text):
            print(f"SKIP {title} (already crud)")
            continue
        new_text = (text.rstrip() + "\n" + CRUD_TAG + "\n") if text else CRUD_TAG + "\n"
        if not args.apply:
            print(f"[DRY] tag {title} into Crud categories")
            edits += 1
            continue
        page.save(new_text, summary=f"Bot: make wikidata-missing category crud "
                                    f"(drain legacy literal tags) {args.run_tag}")
        edits += 1
        print(f"EDIT {title} (tagged crud)")
        time.sleep(THROTTLE)

    print(f"\nDone. Edits: {edits}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
