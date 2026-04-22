#!/usr/bin/env python3
"""
undelete_gaiad_date.py
======================
Kludge: [[Template:GaiadDate]] keeps getting deleted by deletion passes
(Special:UnusedTemplates etc.) even though it must not be deleted. This
script checks whether the page currently exists on shintowiki and, if
it doesn't, issues an action=undelete to restore every deleted revision.

Runs once per pipeline cycle after the Cleanup Loop step that is the
usual culprit for sweeping it up. Requires the `undelete` right —
EmmaBot has sysop, which grants it.

Scope-limited on purpose: this ONLY touches Template:GaiadDate. If some
other page is getting accidentally deleted, handle it in its own script
rather than extending this one.

Standard flags (--apply, --run-tag) are accepted to match the pipeline
convention; --max-edits is ignored because this script operates on one
fixed title.
"""

import argparse
import io
import os
import sys

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
TARGET_TITLE = "Template:GaiadDate"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually undelete. Default is dry-run.")
    parser.add_argument("--max-edits", type=int, default=1,
                        help="Accepted for pipeline parity; ignored.")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for log summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="UndeleteGaiadDateBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    page = site.pages[TARGET_TITLE]
    if page.exists:
        print(f"{TARGET_TITLE} exists; nothing to undelete.")
        return 0

    print(f"{TARGET_TITLE} is currently deleted — attempting undelete.")
    if not args.apply:
        print("DRY RUN: would issue action=undelete.")
        return 0

    token = site.get_token("csrf")
    try:
        resp = site.api(
            "undelete",
            http_method="POST",
            title=TARGET_TITLE,
            reason=f"Template:GaiadDate must not be deleted; auto-restoring {args.run_tag}",
            token=token,
        )
    except Exception as e:
        print(f"UNDELETE FAILED: {e}")
        return 1

    # The API returns {"undelete": {"title": ..., "revisions": N, "fileversions": M, ...}}
    result = (resp or {}).get("undelete") or {}
    revs = result.get("revisions")
    if revs is None:
        print(f"UNDELETE response was unexpected: {resp!r}")
        return 1
    print(f"Undeleted {TARGET_TITLE}: {revs} revision(s) restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
