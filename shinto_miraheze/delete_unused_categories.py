#!/usr/bin/env python3
"""
delete_unused_categories.py
===========================
Deletes category pages returned by Special:UnusedCategories, except pages
containing the template {{Possibly empty category}}.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
THROTTLE = 1.5

POSSIBLY_EMPTY_RE = re.compile(r"\{\{\s*Possibly[_ ]empty[_ ]category\b", re.IGNORECASE)


def iter_unused_categories(site):
    params = {
        "list": "querypage",
        "qppage": "Unusedcategories",
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
        clients_useragent="UnusedCategoryDeleteBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    checked = deleted = skipped = errors = 0
    for title in iter_unused_categories(site):
        if args.max_deletes and deleted >= args.max_deletes:
            print(f"Reached max deletions ({args.max_deletes}); stopping run.")
            break

        checked += 1
        page = site.pages[title]
        prefix = f"[{checked}] {title}"

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading page: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        if POSSIBLY_EMPTY_RE.search(text or ""):
            print(f"{prefix} SKIP ({{{{Possibly empty category}}}} present)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"{prefix} DRY RUN: would delete")
            continue

        try:
            page.delete(
                reason=f"Bot: delete unused category (excluding {{Possibly empty category}}) {args.run_tag}"
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
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
