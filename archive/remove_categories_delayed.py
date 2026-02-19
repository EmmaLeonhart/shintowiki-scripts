#!/usr/bin/env python3
"""
Wait 2 hours, then remove all pages from specified categories
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

# Categories to clear
CATEGORIES_TO_CLEAR = [
    '1000 shortest pages as of Nov 16, 2025',
    'Lonely Pages 2025-12-06',
    'Qq',
    'Has wikidata'
]

# Wait time in seconds (2 hours = 7200 seconds)
WAIT_TIME = 7200

def remove_category_from_page(page, category_name):
    """Remove a category from a page"""
    text = page.text()
    original_text = text

    # Remove category in various formats
    # [[Category:Name]]
    # [[Category:Name|sortkey]]
    pattern = re.compile(r'\[\[Category:' + re.escape(category_name) + r'(?:\|[^\]]+)?\]\]\n?', re.IGNORECASE)
    text = pattern.sub('', text)

    return text != original_text, text

def process_category(site, category_name):
    """Remove all pages from a category"""
    print(f"\n{'='*80}")
    print(f"Processing: [[Category:{category_name}]]")
    print('='*80)
    print()

    try:
        category = site.categories[category_name]
        pages = list(category)
        print(f"Found {len(pages)} pages in category", flush=True)
        print()

        removed_count = 0
        skipped_count = 0

        for i, page in enumerate(pages, 1):
            page_title = page.name
            print(f"[{i}/{len(pages)}] Processing: {page_title}", flush=True)

            if not page.exists:
                print(f"  Page doesn't exist, skipping", flush=True)
                skipped_count += 1
                continue

            changed, new_text = remove_category_from_page(page, category_name)

            if changed:
                page.save(new_text, summary=f'Bot: Remove [[Category:{category_name}]]')
                print(f"  ✓ Removed category", flush=True)
                removed_count += 1
                time.sleep(1.5)
            else:
                print(f"  Category not found in page", flush=True)
                skipped_count += 1

        print()
        print(f"Category [[Category:{category_name}]] complete:")
        print(f"  Removed: {removed_count}")
        print(f"  Skipped: {skipped_count}")

        return removed_count, skipped_count

    except Exception as e:
        print(f"ERROR processing category {category_name}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 0, 0

def main():
    print("=" * 80)
    print("DELAYED CATEGORY REMOVAL")
    print("=" * 80)
    print()
    print(f"Waiting 2 hours ({WAIT_TIME} seconds) before processing...")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Wait 2 hours
    time.sleep(WAIT_TIME)

    print()
    print("=" * 80)
    print("WAIT COMPLETE - STARTING CATEGORY REMOVAL")
    print("=" * 80)
    print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    total_removed = 0
    total_skipped = 0

    for category_name in CATEGORIES_TO_CLEAR:
        removed, skipped = process_category(site, category_name)
        total_removed += removed
        total_skipped += skipped

    print()
    print("=" * 80)
    print("ALL CATEGORIES PROCESSED")
    print("=" * 80)
    print(f"Total pages processed: {total_removed + total_skipped}")
    print(f"Total removed: {total_removed}")
    print(f"Total skipped: {total_skipped}")
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

if __name__ == '__main__':
    main()
