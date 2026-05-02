#!/usr/bin/env python3
"""
undelete_immanuelle_common_js.py
================================
Kludge: [[User:Immanuelle/common.js]] keeps getting deleted by something
in the orchestrator pipeline (suspected: history_offload's delete stage
runs but the recreate stage glitches out, leaving the page in the deleted
pool). Until the underlying bug is identified, this script restores the
page on every pipeline cycle so users don't notice it missing for long.

Standard flags (--apply, --run-tag) are accepted to match the pipeline
convention; --max-edits is ignored because this script operates on one
fixed title.

Modeled directly on shinto_miraheze/undelete_gaiad_date.py — same shape
of fix for the same kind of accidental-deletion glitch. If a third page
ever ends up in this category, factor the shared logic out instead of
copy-pasting again.
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
TARGET_TITLE = "User:Immanuelle/common.js"


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
        clients_useragent="UndeleteImmanuelleCommonJsBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    page = site.pages[TARGET_TITLE]
    if page.exists:
        print(f"{TARGET_TITLE} exists; nothing to undelete.")
        return 0

    print(f"{TARGET_TITLE} is currently deleted - attempting undelete.")
    if not args.apply:
        print("DRY RUN: would issue action=undelete.")
        return 0

    token = site.get_token("csrf")
    try:
        resp = site.api(
            "undelete",
            http_method="POST",
            title=TARGET_TITLE,
            reason=(
                "User:Immanuelle/common.js must not be deleted; "
                f"auto-restoring (orchestrator delete-without-recreate glitch) {args.run_tag}"
            ),
            token=token,
        )
    except Exception as e:
        print(f"UNDELETE FAILED: {e}")
        return 1

    result = (resp or {}).get("undelete") or {}
    revs = result.get("revisions")
    if revs is None:
        print(f"UNDELETE response was unexpected: {resp!r}")
        return 1
    print(f"Undeleted {TARGET_TITLE}: {revs} revision(s) restored.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
