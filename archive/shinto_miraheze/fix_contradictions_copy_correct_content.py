#!/usr/bin/env python3
"""
fix_contradictions_copy_correct_content.py
===========================================
For each contradiction, copy the content from the correct page to the main page
"""

import mwclient
import csv
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Read contradictions
contradictions = []
with open('contradictions_with_expected_enhanced.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        contradictions.append(row)

print(f"Read {len(contradictions)} contradictions\n")

# Process each contradiction
successful = 0
failed = 0
skipped = 0

for i, contradiction in enumerate(contradictions, 1):
    wrong_page = contradiction['Page']
    correct_page = contradiction['Correct Page']
    expected_qid = contradiction['Expected QID']
    wrong_qid = contradiction['Actual QID']

    # Skip if correct page not found
    if correct_page == 'NOT FOUND':
        print(f"{i}. Skipping [[{wrong_page}]] - correct page not found\n")
        skipped += 1
        continue

    # Handle multiple correct pages (separated by |)
    if '|' in correct_page:
        correct_page = correct_page.split('|')[0]  # Use first one

    print(f"{i}. Processing [[{wrong_page}]]...")
    print(f"   Copying from [[{correct_page}]] to [[{wrong_page}]]\n")

    try:
        # Get the content of the correct page
        source_page = site.Pages[correct_page]
        source_content = source_page.text()

        # Get the main page
        main_page = site.Pages[wrong_page]

        # Edit the main page with the content from correct page
        summary = f"Fix QID: replace with correct content from [[{correct_page}]] (wikidata link|{expected_qid})"
        main_page.edit(source_content, summary)

        print(f"   ✓ Updated [[{wrong_page}]] with content from [[{correct_page}]]\n")
        successful += 1

    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        failed += 1

    time.sleep(1.5)

print(f"\n=== Summary ===")
print(f"Successfully updated: {successful}/{len(contradictions)}")
print(f"Failed: {failed}/{len(contradictions)}")
print(f"Skipped (not found): {skipped}/{len(contradictions)}")
