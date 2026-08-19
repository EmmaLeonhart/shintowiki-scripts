#!/usr/bin/env python3
"""
sunset_templates_not_transcluded_in_mainspace_cat.py
=====================================================
Tiny one-shot: adds ``[[Category:crud categories]]`` to
``Category:Templates not transcluded in mainspace``, marking the
older "mainspace-only" version of the category for crud sunset.

Intended to run on/after 2027-07-01 — by that time
``tag_templates_not_transcluded_anywhere.py`` will have populated
``Category:Templates not transcluded in mainspace or categoryspace``
(the narrower, more useful signal for deletion), and the older
"in mainspace" category becomes redundant.

Pairs with ``sunset_jp_char_count_cats.py`` for the same pattern:
small targeted sweeps that drop a single ``[[Category:crud categories]]``
tag onto a known category page so the crud-deletion pipeline can pick
it up. No date check inside the script — the user fires it manually
when they're ready (the date is in the queue plan, not enforced here,
so a slipped timeline doesn't require code changes).

Standard flags: ``--apply`` (default dry-run), ``--run-tag``.
"""

import argparse
import io
import os
import sys

import mwclient
from wiki_login import login_with_retry

from shinto_miraheze.user_agent import USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USER_AGENT = USER_AGENT

TARGET_CATEGORY = "Category:Templates not transcluded in mainspace"
CRUD_CAT = "[[Category:crud categories]]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually save edit")
    ap.add_argument("--run-tag", default="manual run")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    login_with_retry(site, username, password)
    print(f"Logged in as {username}")

    page = site.pages[TARGET_CATEGORY]
    if not page.exists:
        print(f"{TARGET_CATEGORY} does not exist; nothing to do.")
        return 0
    text = page.text()

    if CRUD_CAT in text:
        print(f"{TARGET_CATEGORY} already has crud-categories tag; nothing to do.")
        return 0

    new_text = text.rstrip() + "\n" + CRUD_CAT + "\n"
    summary = (
        f"sunset: mark this category as crud now that the narrower "
        f"'in mainspace or categoryspace' category is in use {args.run_tag}"
    ).strip()

    if not args.apply:
        print(f"DRY: would append {CRUD_CAT} to {TARGET_CATEGORY}")
        return 0

    page.save(new_text, summary=summary, minor=False, bot=True)
    print(f"EDIT {TARGET_CATEGORY}: appended crud-categories tag")
    return 0


if __name__ == "__main__":
    sys.exit(main())
