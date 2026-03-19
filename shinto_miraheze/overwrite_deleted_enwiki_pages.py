#!/usr/bin/env python3
"""
overwrite_deleted_enwiki_pages.py
==================================
Overwrites pages on shintowiki with "PLACEHOLDER" content for pages
that were in the reimport list but no longer exist on enwiki.

These pages have erroneous transclusions that can't be fixed by
reimporting (since the source is gone), so we overwrite them to
stop the broken transclusions.

Default mode is dry-run. Use --apply to actually edit.
"""

import argparse
import io
import os
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

USER_AGENT = "EmmaBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Pages that no longer exist on enwiki but may have broken transclusions
# on shintowiki. Overwrite with PLACEHOLDER to stop the errors.
PAGES = [
    "Module:Template wrapper/sandbox/doc",
    "Module:Webarchive/data/sandbox/doc",
    "Module:Webarchive/sandbox/doc",
    "Module:Wikidata/sandbox/doc",
    "Module:WikidataCheck/sandbox/doc",
    "Module:WikidataIB/sandbox/doc",
    "National High School Archery Tournament Girls' Champions",
    "Tokyo University's Historical Precursors",
    "Tokyo University's Sources and Predecessors",
]


def main():
    parser = argparse.ArgumentParser(
        description="Overwrite deleted-on-enwiki pages with PLACEHOLDER."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    edited = skipped = errors = 0

    for title in PAGES:
        try:
            page = site.pages[title]
            text = (page.text() if page.exists else "").strip()
        except Exception as e:
            print(f"  {title} ERROR reading: {e}")
            errors += 1
            continue

        if text == "PLACEHOLDER":
            print(f"  {title} SKIP (already placeholder)")
            skipped += 1
            continue

        if not args.apply:
            print(f"  {title} DRY RUN: would overwrite with PLACEHOLDER")
            continue

        try:
            page.save(
                "PLACEHOLDER\n",
                summary=f"Bot: overwrite page deleted on enwiki with placeholder {args.run_tag}",
            )
            edited += 1
            print(f"  {title} OVERWRITTEN")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"  {title} ERROR saving: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Overwritten: {edited}")
    print(f"Skipped:     {skipped}")
    print(f"Errors:      {errors}")


if __name__ == "__main__":
    main()
