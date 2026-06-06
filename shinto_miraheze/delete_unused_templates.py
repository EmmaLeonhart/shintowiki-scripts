#!/usr/bin/env python3
"""
delete_unused_templates.py
===========================
Deletes template pages returned by Special:UnusedTemplates.

Default mode deletes. Use --dry-run to preview.
"""

import argparse
import io
import os
import sys
import time

import mwclient

from wiki_login import login_with_retry


def _ensure_utf8_stdout():
    """Reconfigure stdout to UTF-8 for Windows runs. Called from main() rather
    than at import time so the module stays import-safe (a module-level
    sys.stdout swap breaks pytest's output capture)."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

# Templates that must NEVER be deleted even when Special:UnusedTemplates lists
# them (e.g. they have zero transclusions because they are substituted, used
# only off-wiki, or otherwise intentionally kept). Special:UnusedTemplates only
# counts transclusions, so a legitimately-kept-but-untranscluded template shows
# up here every cycle. Before this guard, Template:GaiadDate was deleted each run
# and restored by the undelete_gaiad_date.py kludge — this is the root-cause fix.
KEEP_TITLES = {
    "Template:GaiadDate",
}


def is_protected(title):
    """True if `title` is on the never-delete keep-list."""
    return title in KEEP_TITLES


def iter_unused_templates(site):
    params = {
        "list": "querypage",
        "qppage": "Unusedtemplates",
        "qplimit": "max",
    }
    while True:
        data = site.api("query", **params)
        entries = data.get("query", {}).get("querypage", {}).get("results", [])
        for entry in entries:
            title = entry.get("title", "")
            if title:
                yield title
        if "continue" in data:
            params.update(data["continue"])
        else:
            break


def main():
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-deletes", type=int, default=0, help="Max deletions for this run (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for delete summaries.")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete; only report actions.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="UnusedTemplateDeleteBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    checked = deleted = skipped = errors = 0
    for title in iter_unused_templates(site):
        if args.max_deletes and deleted >= args.max_deletes:
            print(f"Reached max deletions ({args.max_deletes}); stopping run.")
            break

        checked += 1
        prefix = f"[{checked}] {title}"

        if is_protected(title):
            print(f"{prefix} SKIP (protected — never delete)")
            skipped += 1
            continue

        page = site.pages[title]

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"{prefix} DRY RUN: would delete")
            continue

        try:
            page.delete(
                reason=f"Bot: delete unused template {args.run_tag}"
            )
            deleted += 1
            print(f"{prefix} DELETED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR deleting: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Checked: {checked}")
    print(f"Deleted: {deleted}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    main()
