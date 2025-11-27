#!/usr/bin/env python3
"""
update_contradictions_page_enhanced.py
=======================================
Update the contradictions page with correct page information
"""

import csv
import mwclient
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
PAGE_NAME = 'User:Immanuelle/QID contradictions'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Read enhanced contradictions CSV
contradictions = []
with open('contradictions_with_expected_enhanced.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        contradictions.append(row)

print(f"Read {len(contradictions)} enhanced contradictions\n")

# Count results
found = sum(1 for c in contradictions if c.get('Correct Page', '') != 'NOT FOUND')
not_found = sum(1 for c in contradictions if c.get('Correct Page', '') == 'NOT FOUND')

# Create wiki page content
wiki_content = "== QID Contradictions Report ==\n\n"
wiki_content += "This page lists pages where the actual Wikidata QID does not match the expected mapping.\n"
wiki_content += "For each contradiction, the correct page (that actually has the expected QID) is also listed.\n\n"
wiki_content += f"'''Total contradictions found: {len(contradictions)}'''\n"
wiki_content += f"* Pages with correct page found: {found}\n"
wiki_content += f"* Pages where correct page not found: {not_found}\n\n"

wiki_content += "=== Summary Table ===\n\n"
wiki_content += "{| class=\"wikitable sortable\"\n"
wiki_content += "|-\n"
wiki_content += "! # !! Wrong Page !! Expected QID !! Actual QID !! Correct Page(s)\n"

for i, contradiction in enumerate(contradictions, 1):
    page = contradiction['Page']
    expected = contradiction['Expected QID']
    actual = contradiction['Actual QID']
    correct_pages = contradiction.get('Correct Page', 'NOT FOUND')

    wiki_content += "|-\n"
    wiki_content += f"| {i} || [[{page}]] || {{{{wikidata link|{expected}}}}} || {{{{wikidata link|{actual}}}}} || "

    if correct_pages != 'NOT FOUND':
        # Split multiple pages if separated by |
        pages_list = correct_pages.split('|')
        correct_links = ', '.join(f'[[{p}]]' for p in pages_list)
        wiki_content += correct_links
    else:
        wiki_content += "NOT FOUND"

    wiki_content += "\n"

wiki_content += "|}\n\n"

# Add details section
wiki_content += "=== Detailed Breakdown ===\n\n"
for i, contradiction in enumerate(contradictions, 1):
    page = contradiction['Page']
    expected = contradiction['Expected QID']
    actual = contradiction['Actual QID']
    correct_pages = contradiction.get('Correct Page', 'NOT FOUND')

    wiki_content += f"==== {i}. [[{page}]] ====\n"
    wiki_content += f"* '''Wrong QID''': {{{{wikidata link|{actual}}}}}\n"
    wiki_content += f"* '''Expected QID''': {{{{wikidata link|{expected}}}}}\n"

    if correct_pages != 'NOT FOUND':
        pages_list = correct_pages.split('|')
        correct_links = ', '.join(f'[[{p}]]' for p in pages_list)
        wiki_content += f"* '''Correct Page(s)''': {correct_links}\n"
    else:
        wiki_content += f"* '''Correct Page(s)''': NOT FOUND (may not be in exported data)\n"

    wiki_content += "\n"

# Upload to wiki
print(f"Uploading enhanced report to [[{PAGE_NAME}]]...\n")
page = site.Pages[PAGE_NAME]
page.edit(wiki_content, "Update QID contradictions report with correct pages")

print(f"Successfully uploaded!\n")
time.sleep(1.5)

print("Done!")
