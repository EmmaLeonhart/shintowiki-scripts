#!/usr/bin/env python3
"""
categorize_uncategorized_pages.py
==================================
Fetches Special:UncategorizedPages via the querypage API and tags each
page with [[Category:Uncategorized pages]].

Processes up to --max-edits pages per run (default 100).

Default mode is dry-run. Use --apply to actually edit.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 1.5

TARGET_CAT = "Uncategorized pages"
CAT_TAG = f"[[Category:{TARGET_CAT}]]"

USER_AGENT = "UncategorizedPagesBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)
CATEGORY_RE = re.compile(r'\[\[\s*Category\s*:', re.IGNORECASE)


# ─── HELPERS ────────────────────────────────────────────────

def iter_uncategorized_pages(site):
    """Yield page titles from Special:UncategorizedPages."""
    params = {
        "list": "querypage",
        "qppage": "Uncategorizedpages",
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


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tag uncategorized pages with [[Category:Uncategorized pages]]."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max pages to edit per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    edited = skipped = errors = 0
    checked = 0

    for title in iter_uncategorized_pages(site):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        checked += 1
        prefix = f"[{checked}] {title}"

        try:
            page = site.pages[title]
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        # Skip redirects
        if REDIRECT_RE.search(text):
            print(f"{prefix} SKIP (redirect)")
            skipped += 1
            continue

        # Skip if already has a category (shouldn't happen but be safe)
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
                summary=f"Bot: categorize uncategorized page {args.run_tag}",
            )
            edited += 1
            print(f"{prefix} TAGGED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Checked:  {checked}")
    print(f"Tagged:   {edited}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
