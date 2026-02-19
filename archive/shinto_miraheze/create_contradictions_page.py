#!/usr/bin/env python3
"""
create_contradictions_page.py
=============================
Create a wiki page for QID contradictions with expected mappings
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

# Read contradictions CSV
contradictions = []
with open('contradictions_with_expected.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        contradictions.append(row)

print(f"Read {len(contradictions)} contradictions\n")

# Create wiki page content
wiki_content = "== QID Contradictions Report ==\n\n"
wiki_content += "This page lists pages where the actual Wikidata QID does not match the expected mapping.\n\n"
wiki_content += f"'''Total contradictions found: {len(contradictions)}'''\n\n"

wiki_content += "=== Contradictions ===\n\n"
wiki_content += "{| class=\"wikitable sortable\"\n"
wiki_content += "|-\n"
wiki_content += "! Page !! Expected QID !! Actual QID\n"

for contradiction in contradictions:
    page = contradiction['Page']
    expected = contradiction['Expected QID']
    actual = contradiction['Actual QID']

    wiki_content += "|-\n"
    wiki_content += f"| [[{page}]] || {{{{wikidata link|{expected}}}}} || {{{{wikidata link|{actual}}}}}\n"

wiki_content += "|}\n\n"

# Add details section
wiki_content += "=== Details ===\n\n"
for i, contradiction in enumerate(contradictions, 1):
    page = contradiction['Page']
    expected = contradiction['Expected QID']
    actual = contradiction['Actual QID']

    wiki_content += f"==== {i}. [[{page}]] ====\n"
    wiki_content += f"* Expected: {{{{wikidata link|{expected}}}}}\n"
    wiki_content += f"* Actual: {{{{wikidata link|{actual}}}}}\n"
    wiki_content += "\n"

# Upload to wiki
print(f"Uploading to [[{PAGE_NAME}]]...\n")
page = site.Pages[PAGE_NAME]
page.edit(wiki_content, "Create QID contradictions report")

print(f"Successfully uploaded!\n")
time.sleep(1.5)

print("Done!")
