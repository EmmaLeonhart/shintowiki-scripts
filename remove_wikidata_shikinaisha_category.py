#!/usr/bin/env python3
"""
Remove [[Category:Wikidata generated shikinaisha pages]] from all pages in Category:Automerged Japanese text
With 1 minute delay between edits to avoid race conditions
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

# Delay between edits (60 seconds = 1 minute)
EDIT_DELAY = 60

def remove_category(text, category_name):
    """Remove a specific category from page text"""
    # Pattern to match [[Category:NAME]] with optional whitespace/newlines
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]\n?'
    new_text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return new_text

def main():
    print("=" * 80)
    print("REMOVE WIKIDATA GENERATED SHIKINAISHA PAGES CATEGORY")
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

    removed = 0
    skipped = 0
    failed = 0

    for i, page in enumerate(pages, 1):
        page_title = page.name
        print(f"[{i}/{len(pages)}] Processing: [[{page_title}]]", flush=True)

        if not page.exists:
            print(f"  ✗ Page doesn't exist, skipping", flush=True)
            skipped += 1
            continue

        try:
            # Get page text
            text = page.text()

            # Check if category exists
            if '[[Category:Wikidata generated shikinaisha pages]]' not in text:
                print(f"  Category not found, skipping", flush=True)
                skipped += 1
                continue

            # Remove the category
            new_text = remove_category(text, 'Wikidata generated shikinaisha pages')

            if new_text == text:
                print(f"  No changes made", flush=True)
                skipped += 1
                continue

            # Save the page
            page.save(new_text, summary='Remove [[Category:Wikidata generated shikinaisha pages]]')
            print(f"  ✓ Removed category", flush=True)

            removed += 1

            # Wait 60 seconds between edits to avoid race conditions
            if i < len(pages):  # Don't wait after the last page
                print(f"  Waiting 60 seconds before next edit...", flush=True)
                time.sleep(EDIT_DELAY)

        except Exception as e:
            print(f"  ✗ Failed: {e}", flush=True)
            failed += 1

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pages found: {len(pages)}")
    print(f"Categories removed: {removed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print()

if __name__ == '__main__':
    main()
