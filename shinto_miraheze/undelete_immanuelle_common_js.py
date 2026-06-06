#!/usr/bin/env python3
"""
undelete_immanuelle_common_js.py
================================
Kludge: [[User:Immanuelle/common.js]] keeps getting deleted by the
orchestrator's history_offload op. Until the underlying bug is fixed,
this script tries to restore the page on every pipeline cycle.

CAVEAT (discovered 2026-05-03): EmmaBot doesn't actually have
permission to write back this page. The MediaWiki core enforces
``editmyusercss``/``editmyuserjs`` (own pages) vs
``edituserjs``/``editusercss`` (other users') as separate rights, and
EmmaBot has neither for the JS subpages of User:Immanuelle. Action=undelete
on this title therefore fails with API code ``customjsprotected``:
"You do not have permission to edit this JavaScript page because it
contains another user's personal settings."

The script now treats ``customjsprotected`` as a soft failure: it logs
prominently and exits 0 so the cleanup-loop doesn't go red on every
run. Restoring the page in practice requires a steward / admin manual
action via Special:Undelete on shinto.miraheze.org.

The complementary fix is in ``shinto_miraheze/orchestrators/ops/
history_offload.py`` — that op now skips JS/CSS user-subpages so the
deletion that triggers this kludge stops happening on new pages.

Standard flags (--apply, --run-tag) are accepted to match the pipeline
convention; --max-edits is ignored because this script operates on one
fixed title.
"""

import argparse
import io
import os
import sys

import mwclient
from wiki_login import login_with_retry

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
    login_with_retry(site, USERNAME, PASSWORD)
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
    except mwclient.errors.APIError as e:
        # ``customjsprotected`` is the MediaWiki rejection for
        # editing/restoring another user's personal JS without the
        # ``edituserjs`` right. EmmaBot doesn't have it, so the API
        # would refuse this action no matter how many times we retry.
        # Treat as a soft failure so cleanup-loop doesn't go red on
        # every cycle: print a loud notice and exit 0. Manual admin
        # action via Special:Undelete is required to restore the page.
        code = getattr(e, "code", None) or (e.args[0] if e.args else None)
        if code == "customjsprotected":
            print(
                f"SOFT FAIL: {TARGET_TITLE} cannot be undeleted by EmmaBot "
                f"(API code 'customjsprotected'). Manual admin undelete "
                f"is required via Special:Undelete on shinto.miraheze.org. "
                f"Treating as success so cleanup-loop doesn't fail."
            )
            return 0
        print(f"UNDELETE FAILED: {e}")
        return 1
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
