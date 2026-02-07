#!/usr/bin/env python3
"""
add_qq_to_lists.py
==================
Adds [[Category:qq]] to all "List of Shikinaisha in" pages.
"""

import mwclient
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.0

CATEGORY_TO_ADD = "[[Category:qq]]"
EDIT_SUMMARY = "adding dummy category to make categories work"

def main():
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    # Get all "List of Shikinaisha in" pages
    pages = list(site.allpages(prefix="List of Shikinaisha in"))
    print(f"Found {len(pages)} list pages\n")

    success = 0
    skipped = 0
    failed = 0

    for i, page in enumerate(pages, 1):
        page_title = page.name
        print(f"[{i}/{len(pages)}] {page_title}", end=" ... ", flush=True)

        try:
            content = page.text()

            # Check if already has the category
            if "[[Category:qq]]" in content:
                print("SKIP (already has)")
                skipped += 1
                continue

            # Add category at the end
            new_content = content.rstrip() + "\n" + CATEGORY_TO_ADD

            page.save(new_content, summary=EDIT_SUMMARY)
            print("OK")
            success += 1

        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        time.sleep(SLEEP)

    print(f"\n{'='*50}")
    print(f"Summary: {success} updated, {skipped} skipped, {failed} failed")

if __name__ == "__main__":
    main()
