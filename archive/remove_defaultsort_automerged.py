#!/usr/bin/env python3
"""
Remove DEFAULTSORT and デフォルトソート templates from Category:Automerged Japanese text
"""

import sys
import io
import time
import re
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def main():
    print("=" * 80)
    print("REMOVE DEFAULTSORT TEMPLATES FROM AUTOMERGED JAPANESE TEXT")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Get all pages in category
    category_name = 'Automerged Japanese text'
    print(f"Fetching pages from [[Category:{category_name}]]...", flush=True)
    category = site.categories[category_name]
    pages = list(category)
    print(f"Found {len(pages)} pages to process", flush=True)
    print()

    # Regex patterns for both English and Japanese DEFAULTSORT
    defaultsort_pattern = re.compile(r'\{\{DEFAULTSORT:[^}]+\}\}\n?', re.IGNORECASE)
    ja_defaultsort_pattern = re.compile(r'\{\{デフォルトソート:[^}]+\}\}\n?')

    edited_count = 0
    skipped_count = 0

    for i, page in enumerate(pages, 1):
        page_title = page.name
        print(f"[{i}/{len(pages)}] Processing: {page_title}", flush=True)

        if not page.exists:
            print(f"  Page doesn't exist, skipping", flush=True)
            skipped_count += 1
            continue

        text = page.text()
        original_text = text

        # Remove English DEFAULTSORT
        text = defaultsort_pattern.sub('', text)

        # Remove Japanese デフォルトソート
        text = ja_defaultsort_pattern.sub('', text)

        if text != original_text:
            # Save the changes
            page.save(text, summary='Bot: Remove DEFAULTSORT and デフォルトソート templates from automerged pages')
            print(f"  ✓ Removed DEFAULTSORT templates", flush=True)
            edited_count += 1
            time.sleep(1.5)
        else:
            print(f"  No DEFAULTSORT templates found", flush=True)
            skipped_count += 1

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Total pages: {len(pages)}")
    print(f"Edited: {edited_count}")
    print(f"Skipped: {skipped_count}")
    print()

if __name__ == '__main__':
    main()
