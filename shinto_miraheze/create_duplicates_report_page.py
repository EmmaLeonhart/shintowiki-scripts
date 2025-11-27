#!/usr/bin/env python3
"""
create_duplicates_report_page.py
================================
Create a wiki page listing all duplicate QIDs with their pages
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
PAGE_NAME = 'User:Immanuelle/Duplicate QIDs'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Read duplicate QIDs CSV
duplicates = []
with open('duplicate_qids.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        duplicates.append(row)

print(f"Read {len(duplicates)} duplicate QID sets\n")

# Create wiki page content
wiki_content = "== Duplicate QIDs Report ==\n\n"
wiki_content += "This page lists all Wikidata QIDs that are linked from multiple pages.\n\n"
wiki_content += f"'''Total QID sets with duplicates: {len(duplicates)}'''\n\n"

wiki_content += "=== Summary Table ===\n\n"
wiki_content += "{| class=\"wikitable sortable\"\n"
wiki_content += "|-\n"
wiki_content += "! # !! QID !! Count !! Pages\n"

for i, duplicate in enumerate(duplicates, 1):
    qid = duplicate['QID']
    count = duplicate['Count']

    # Get all pages for this QID
    pages = []
    for key in duplicate:
        if key.startswith('Page'):
            page = duplicate[key]
            if page:  # Check if not None/empty before stripping
                page = page.strip() if isinstance(page, str) else page
                if page:
                    pages.append(page)

    pages_list = ', '.join(f'[[{p}]]' for p in pages)

    wiki_content += "|-\n"
    wiki_content += f"| {i} || {qid} || {count} || {pages_list}\n"

wiki_content += "|}\n\n"

# Add detailed section
wiki_content += "=== Detailed Breakdown ===\n\n"
for i, duplicate in enumerate(duplicates, 1):
    qid = duplicate['QID']
    count = duplicate['Count']

    # Get all pages for this QID
    pages = []
    for key in duplicate:
        if key.startswith('Page'):
            page = duplicate[key]
            if page:  # Check if not None/empty before stripping
                page = page.strip() if isinstance(page, str) else page
                if page:
                    pages.append(page)

    wiki_content += f"==== {i}. {qid} ({count} pages) ====\n"
    for page in pages:
        wiki_content += f"* [[{page}]]\n"
    wiki_content += "\n"

# Upload to wiki
print(f"Uploading duplicate QIDs report to [[{PAGE_NAME}]]...\n")
page = site.Pages[PAGE_NAME]
page.edit(wiki_content, "Create duplicate QIDs report")

print(f"Successfully uploaded!\n")
time.sleep(1.5)

print("Done!")
