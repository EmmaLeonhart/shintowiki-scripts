#!/usr/bin/env python3
"""
Move Q brackets pages to English labels and create redirects
"""

import sys
import io
import csv
import time
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
    print("MOVE Q BRACKETS PAGES TO ENGLISH LABELS")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Read CSV
    csv_filename = 'q_brackets_analysis.csv'
    print(f"Reading {csv_filename}...", flush=True)

    moves = []
    with open(csv_filename, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            original_title = row['Original Title']
            proposed_title = row['Proposed New Title']

            if proposed_title and proposed_title.strip():
                moves.append((original_title, proposed_title))

    print(f"Found {len(moves)} pages to move", flush=True)
    print()

    moved = 0
    skipped = 0
    failed = 0

    for i, (old_title, new_title) in enumerate(moves, 1):
        print(f"[{i}/{len(moves)}] Moving: [[{old_title}]] → [[{new_title}]]", flush=True)

        # Check if source page exists
        old_page = site.pages[old_title]
        if not old_page.exists:
            print(f"  ✗ Source page doesn't exist, skipping", flush=True)
            skipped += 1
            continue

        # Check if target page already exists
        new_page = site.pages[new_title]
        if new_page.exists:
            print(f"  ✗ Target page already exists, skipping", flush=True)
            skipped += 1
            continue

        try:
            # Move the page (creates redirect at old location)
            old_page.move(
                new_title,
                reason='Replace QID with English place name for better readability',
                no_redirect=False  # Create redirect at old location
            )
            print(f"  ✓ Moved successfully (redirect created at old title)", flush=True)
            moved += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"  ✗ Move failed: {e}", flush=True)
            failed += 1

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pages to move: {len(moves)}")
    print(f"Successfully moved: {moved}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print()

if __name__ == '__main__':
    main()
