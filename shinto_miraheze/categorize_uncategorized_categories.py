#!/usr/bin/env python3
"""
categorize_uncategorized_categories.py
======================================
Fetches Special:UncategorizedCategories via the querypage API and appends
[[Category:Categories autocreated by EmmaBot]] to each page that lacks
any category membership.

Many of these categories were created in earlier bulk workflows without
proper categorization. This script retroactively fixes that.

Default mode is dry-run. Use --apply to save edits.
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
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

TARGET_CAT = "Categories autocreated by EmmaBot"
CAT_TAG = f"[[Category:{TARGET_CAT}]]"

# Match any [[Category:...]] already present
CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:", re.IGNORECASE)


def iter_uncategorized_categories(site):
    """Yield category titles from Special:UncategorizedCategories."""
    params = {
        "list": "querypage",
        "qppage": "Uncategorizedcategories",
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
    parser.add_argument("--apply", action="store_true", help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=0, help="Max pages to edit (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="UncategorizedCategoryBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    checked = edited = skipped = errors = 0
    for title in iter_uncategorized_categories(site):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        checked += 1
        prefix = f"[{checked}] {title}"

        page = site.pages[title]

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        if CATEGORY_RE.search(text):
            print(f"{prefix} SKIP (already has a category)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would add {CAT_TAG}")
            continue

        try:
            new_text = text.rstrip() + "\n" + CAT_TAG + "\n" if text.strip() else CAT_TAG + "\n"
            page.save(
                new_text,
                summary=f"Bot: categorize uncategorized category {args.run_tag}",
            )
            edited += 1
            print(f"{prefix} EDITED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Checked: {checked}")
    print(f"Edited:  {edited}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    main()
