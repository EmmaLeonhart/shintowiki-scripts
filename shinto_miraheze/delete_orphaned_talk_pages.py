#!/usr/bin/env python3
"""
delete_orphaned_talk_pages.py
==============================
Deletes talk pages listed on Special:OrphanedTalkPages — talk pages
whose corresponding subject page does not exist.

Default mode deletes. Use --dry-run to preview.
"""

import argparse
import io
import os
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5


def iter_orphaned_talk_pages(site):
    """Yield page titles from Special:OrphanedTalkPages."""
    params = {
        "list": "querypage",
        "qppage": "OrphanedTalkPages",
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-deletes", type=int, default=0, help="Max deletions for this run (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for delete summaries.")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete; only report actions.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="OrphanedTalkDeleteBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    checked = deleted = skipped = errors = 0
    for title in iter_orphaned_talk_pages(site):
        if args.max_deletes and deleted >= args.max_deletes:
            print(f"Reached max deletions ({args.max_deletes}); stopping run.")
            break

        checked += 1
        page = site.pages[title]
        prefix = f"[{checked}] {title}"

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"{prefix} DRY RUN: would delete")
            continue

        try:
            page.delete(
                reason=f"Bot: delete orphaned talk page (subject page does not exist) {args.run_tag}"
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
