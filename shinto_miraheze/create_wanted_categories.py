#!/usr/bin/env python3
"""
create_wanted_categories.py
============================
Fetches Special:WantedCategories via the querypage API and creates stub
category pages for each entry.

Each created page gets:
    [[Category:Categories autocreated by EmmaBot]]

Default mode is dry-run. Use --apply to save edits.
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
THROTTLE = 1.5

PARENT_CAT = "Categories autocreated by EmmaBot"
CONTENT = f"[[Category:{PARENT_CAT}]]"


def iter_wanted_categories(site):
    """Yield category titles from Special:WantedCategories."""
    params = {
        "list": "querypage",
        "qppage": "Wantedcategories",
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
    parser.add_argument("--apply", action="store_true", help="Actually create pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=0, help="Max pages to create (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="WantedCategoryBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Ensure parent category exists
    parent_page = site.pages[f"Category:{PARENT_CAT}"]
    if not parent_page.exists:
        if args.apply:
            parent_page.save(
                f"Category for pages autocreated by [[User:EmmaBot]].",
                summary=f"Bot: create autocreated-categories tracking category {args.run_tag}",
            )
            print(f"CREATED parent: Category:{PARENT_CAT}")
            time.sleep(THROTTLE)
        else:
            print(f"DRY RUN: would create parent Category:{PARENT_CAT}")
    else:
        print(f"Parent category already exists: Category:{PARENT_CAT}")

    print()

    checked = created = skipped = errors = 0
    for title in iter_wanted_categories(site):
        if args.max_edits and created >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        checked += 1
        prefix = f"[{checked}] {title}"

        # Title from the API is already in "Category:Foo" form
        page = site.pages[title]

        if page.exists:
            print(f"{prefix} SKIP (already exists)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would create")
            continue

        try:
            page.save(
                CONTENT,
                summary=f"Bot: create wanted category {args.run_tag}",
            )
            created += 1
            print(f"{prefix} CREATED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Checked: {checked}")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    main()
