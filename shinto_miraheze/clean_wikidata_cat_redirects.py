#!/usr/bin/env python3
"""
clean_wikidata_cat_redirects.py
================================
Scans [[Category:Pages without wikidata]] and removes the category tag
from any page that is a redirect. Redirects should never be in this
category — they don't need their own wikidata link.

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

USER_AGENT = "WikidataCatCleanBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

CATEGORY_NAME = "Pages without wikidata"

REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)
CAT_TAG_RE = re.compile(
    r'\n?\[\[\s*Category\s*:\s*Pages without wikidata\s*\]\]\n?',
    re.IGNORECASE,
)


# ─── HELPERS ────────────────────────────────────────────────

def iter_category_members(site, category_name):
    """Yield all page titles in a category."""
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category_name}",
        "cmlimit": 500,
        "format": "json",
    }
    while True:
        data = site.api("query", **params)
        for m in data.get("query", {}).get("categorymembers", []):
            yield m["title"]
        if "continue" in data:
            params.update(data["continue"])
        else:
            break


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove [[Category:Pages without wikidata]] from redirects."
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

    for title in iter_category_members(site, CATEGORY_NAME):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        checked += 1

        try:
            page = site.pages[title]
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"[{checked}] {title} ERROR reading: {e}")
            errors += 1
            continue

        if not page.exists:
            skipped += 1
            continue

        if not REDIRECT_RE.search(text):
            skipped += 1
            continue

        # It's a redirect with the category — remove the category tag
        new_text = CAT_TAG_RE.sub('', text)

        # Clean up trailing whitespace
        new_text = new_text.rstrip() + "\n"

        if new_text.strip() == text.strip():
            skipped += 1
            continue

        if not args.apply:
            print(f"[{checked}] {title} DRY RUN: would remove category from redirect")
            continue

        try:
            page.save(
                new_text,
                summary=f"Bot: remove [[Category:Pages without wikidata]] from redirect {args.run_tag}",
            )
            edited += 1
            print(f"[{checked}] {title} CLEANED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Checked:  {checked}")
    print(f"Cleaned:  {edited}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
