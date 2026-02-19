#!/usr/bin/env python3
"""
recreate_categories_wave2.py
============================
Recreates category pages from the downloaded list (Dw69ggsm.txt).
Each category page will contain only: [[Category:Second wave of autocreated categories after wiki restoration]]
"""

import mwclient
import sys
import time
import re

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

# Input file
INPUT_FILE = r'C:\Users\Immanuelle\Downloads\Dw69ggsm.txt'

# Content for each category page
CATEGORY_CONTENT = "[[Category:Second wave of autocreated categories after wiki restoration]]"

def parse_categories(filename):
    """Parse category names from the downloaded file."""
    categories = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Remove member count: "(X members)" or "(X → Y members)"
            match = re.match(r'^(.+?)\s*\(\d[\d,]*(?:\s*→\s*\d[\d,]*)?\s*members?\)$', line)
            if match:
                cat_name = match.group(1).strip()
                categories.append(cat_name)
            else:
                # If no match, use the whole line (shouldn't happen with this file)
                categories.append(line)
    return categories

def main():
    print(f"Reading categories from {INPUT_FILE}...")
    categories = parse_categories(INPUT_FILE)
    print(f"Found {len(categories)} categories\n")

    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    total = len(categories)
    success = 0
    failed = 0
    skipped = 0

    for i, cat_name in enumerate(categories, 1):
        page_title = f"Category:{cat_name}"
        print(f"[{i}/{total}] {page_title}", end=" ... ", flush=True)

        try:
            page = site.pages[page_title]
            if page.exists:
                print("SKIPPED (already exists)")
                skipped += 1
            else:
                page.save(CATEGORY_CONTENT, summary="Bot: Recreate category (second wave) after wiki restoration")
                print("OK")
                success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        time.sleep(SLEEP)

    print(f"\n{'='*50}")
    print(f"Summary: {success} created, {skipped} skipped, {failed} failed out of {total}")

if __name__ == "__main__":
    main()
