#!/usr/bin/env python3
"""
create_qid_disambiguation_pages.py
==================================
For each contradiction, create a QID disambiguation page
by copying the content of the wrong page to a new page with QID in title
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

for i, contradiction in enumerate(contradictions, 1):
    wrong_page = contradiction['Page']
    wrong_qid = contradiction['Actual QID']
    expected_qid = contradiction['Expected QID']

    # Create disambiguation page name
    disambig_page_name = f"{wrong_page} ({wrong_qid})"

    print(f"{i}. Processing [[{wrong_page}]] with {wrong_qid}...")

    try:
        # Get the content of the wrong page
        page = site.Pages[wrong_page]
        page_content = page.text()

        # Create the disambiguation page
        disambig_page = site.Pages[disambig_page_name]

        # Add a note at the top about the QID
        note = f"{{{{wikidata link|{wrong_qid}}}}}\n\n"
        full_content = note + page_content

        # Edit the page
        disambig_page.edit(full_content, f"Create QID disambiguation page (copy from [[{wrong_page}]] with {wrong_qid})")

        print(f"   ✓ Created [[{disambig_page_name}]]\n")
        successful += 1

    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        failed += 1

    time.sleep(1.5)

print(f"\n=== Summary ===")
print(f"Successfully created: {successful}/{len(contradictions)}")
print(f"Failed: {failed}/{len(contradictions)}")
