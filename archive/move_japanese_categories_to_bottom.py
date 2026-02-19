#!/usr/bin/env python3
"""
Move categories from Japanese Wikipedia section to bottom of page
For all pages in Category:Automerged Japanese text
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

def extract_and_move_categories(text):
    """Extract categories from Japanese section and move to bottom"""

    # Find the Japanese Wikipedia content section
    japanese_section_match = re.search(r'(== Japanese Wikipedia content ==.*)', text, re.DOTALL)
    if not japanese_section_match:
        return text, []

    japanese_section_start = japanese_section_match.start()
    japanese_section = japanese_section_match.group(1)

    # Find all categories in the Japanese section
    category_pattern = r'\[\[Category:[^\]]+\]\]\n?'
    categories_in_japanese = re.findall(category_pattern, japanese_section)

    if not categories_in_japanese:
        return text, []

    # Remove categories from Japanese section
    japanese_section_cleaned = japanese_section
    for category in categories_in_japanese:
        japanese_section_cleaned = japanese_section_cleaned.replace(category, '', 1)

    # Rebuild the page: content before Japanese section + cleaned Japanese section + categories at bottom
    before_japanese = text[:japanese_section_start]
    new_text = before_japanese + japanese_section_cleaned

    # Add categories at the very bottom
    for category in categories_in_japanese:
        if not new_text.endswith('\n'):
            new_text += '\n'
        new_text += category

    return new_text, categories_in_japanese

def main():
    print("=" * 80)
    print("MOVE JAPANESE CATEGORIES TO BOTTOM")
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

    processed = 0
    moved = 0
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

            # Extract and move categories
            new_text, categories_moved = extract_and_move_categories(text)

            if not categories_moved:
                print(f"  No categories found in Japanese section", flush=True)
                skipped += 1
                continue

            if new_text == text:
                print(f"  No changes needed", flush=True)
                skipped += 1
                continue

            # Save the page
            page.save(new_text, summary=f'Move {len(categories_moved)} categories from Japanese section to bottom of page')
            print(f"  ✓ Moved {len(categories_moved)} categories to bottom", flush=True)
            for cat in categories_moved:
                print(f"    - {cat.strip()}", flush=True)

            moved += 1
            processed += 1
            time.sleep(1.5)

        except Exception as e:
            print(f"  ✗ Failed: {e}", flush=True)
            failed += 1

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pages found: {len(pages)}")
    print(f"Pages with categories moved: {moved}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print()

if __name__ == '__main__':
    main()
