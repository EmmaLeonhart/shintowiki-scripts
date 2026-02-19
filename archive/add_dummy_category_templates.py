#!/usr/bin/env python3
"""
add_dummy_category_templates.py
===============================
Adds [[Category:Templates]] to the end of every page in the template namespace.
This is a dummy edit to make the categories work after wiki restoration.
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
SLEEP = 1.5  # seconds between edits

CATEGORY_TO_ADD = "[[Category:Templates]]"
EDIT_SUMMARY = "Bot: Adding dummy category to make categories work after wiki restoration"

def main():
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    total_processed = 0
    total_success = 0
    total_failed = 0
    total_skipped = 0

    print("Processing all pages in Template namespace (ns=10)...")

    for page in site.allpages(namespace=10):
        total_processed += 1
        page_title = page.name

        try:
            content = page.text()

            # Check if category already exists
            if "[[Category:Templates]]" in content:
                print(f"[SKIP] {page_title} (already has category)")
                total_skipped += 1
                continue

            # Add the category at the end
            new_content = content.rstrip() + "\n" + CATEGORY_TO_ADD

            page.save(new_content, summary=EDIT_SUMMARY)
            print(f"[OK] {page_title}")
            total_success += 1

        except Exception as e:
            print(f"[FAILED] {page_title}: {e}")
            total_failed += 1

        time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print('='*60)
    print(f"Total processed: {total_processed}")
    print(f"Successfully edited: {total_success}")
    print(f"Skipped (already has category): {total_skipped}")
    print(f"Failed: {total_failed}")

if __name__ == "__main__":
    main()
