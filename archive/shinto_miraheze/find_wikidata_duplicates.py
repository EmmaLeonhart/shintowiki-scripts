#!/usr/bin/env python3
"""
find_wikidata_duplicates.py
============================
Find all pages in [[Category:Pages linked to Wikidata]] and identify
pages that link to the same Wikidata QID (duplicates).
"""

import mwclient
import re
import sys
import time
from collections import defaultdict

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
CATEGORY  = 'Pages linked to Wikidata'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

# ─── MAIN LOGIC ──────────────────────────────────────────────

# Get all pages in the category
print(f"Fetching all pages in [[Category:{CATEGORY}]]...\n")

category = site.Categories[CATEGORY]
pages = list(category)

print(f"Found {len(pages)} pages\n")

# Map QIDs to pages
qid_to_pages = defaultdict(list)

for i, page in enumerate(pages, 1):
    if i % 50 == 0:
        print(f"Processing page {i}/{len(pages)}...")

    try:
        text = page.text()
        qid = extract_wikidata_qid(text)

        if qid:
            qid_to_pages[qid].append(page.name)
    except Exception as e:
        print(f"Error processing {page.name}: {e}")

    time.sleep(1.5)

# Find duplicates (QIDs with 2+ pages)
duplicates = {qid: pages for qid, pages in qid_to_pages.items() if len(pages) >= 2}

print(f"\nFound {len(duplicates)} QIDs with duplicate links")

# Sort by number of pages (descending), then by QID
sorted_duplicates = sorted(duplicates.items(),
                          key=lambda x: (-len(x[1]), x[0]))

# Generate wiki markup
wiki_content = "== Wikidata Duplicates ==\n\n"
wiki_content += "This page lists all Wikidata QIDs that are linked from multiple pages in [[Category:Pages linked to Wikidata]].\n\n"
wiki_content += f"Total duplicate QIDs: {len(duplicates)}\n\n"

for qid, page_list in sorted_duplicates:
    wiki_content += f"=== {qid} ===\n"
    wiki_content += f"{{{{wikidata link|{qid}}}}}\n\n"

    for page_name in sorted(page_list):
        wiki_content += f"* [[{page_name}]]\n"

    wiki_content += "\n"

# Write to file
with open('Wikidata_duplicates_page_new.wiki', 'w', encoding='utf-8') as f:
    f.write(wiki_content)

print(f"\nWrote {len(wiki_content)} characters to Wikidata_duplicates_page_new.wiki")
print(f"\nDuplicate summary:")
print(f"- Total QIDs with duplicates: {len(duplicates)}")
print(f"- Most duplicated: {sorted_duplicates[0][0]} ({len(sorted_duplicates[0][1])} pages)")
