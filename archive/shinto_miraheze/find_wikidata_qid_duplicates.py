#!/usr/bin/env python3
"""
find_wikidata_qid_duplicates.py
================================
1. Check every page in [[Category:Pages linked to Wikidata]]
2. Extract the Wikidata QID
3. If a page has conflicting QIDs, add it to [[Category:pages with conflicting qids]]
4. Generate a CSV with QID in first column, all pages linking to it in subsequent columns
5. Generate and upload a wiki page with the duplicate report
"""

import mwclient
import re
import sys
import time
import csv
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
CONFLICT_CAT = 'pages with conflicting qids'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_all_wikidata_qids(page_text):
    """Extract all Wikidata QIDs from page text."""
    matches = re.findall(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    qids = [match[0].upper() for match in matches]
    return qids

# ─── MAIN LOGIC ──────────────────────────────────────────────

# Get all pages in the category
print(f"Fetching all pages in [[Category:{CATEGORY}]]...\n")

category = site.Categories[CATEGORY]
pages = list(category)

print(f"Found {len(pages)} pages\n")

# Map QID to pages
qid_to_pages = defaultdict(list)
conflicting_pages = []

for i, page in enumerate(pages, 1):
    if i % 100 == 0:
        print(f"Processing page {i}/{len(pages)}...")

    try:
        text = page.text()
        qids = extract_all_wikidata_qids(text)

        if len(qids) > 1:
            # Page has conflicting QIDs
            print(f"  → Conflict on {page.name}: {qids}")
            conflicting_pages.append(page.name)
        elif len(qids) == 1:
            # Single QID - add to mapping
            qid_to_pages[qids[0]].append(page.name)
    except Exception as e:
        print(f"Error processing {page.name}: {e}")

    time.sleep(1.5)

print(f"\nFound {len(conflicting_pages)} pages with conflicting QIDs")

# Add conflicting pages to category
if conflicting_pages:
    print(f"Adding conflicting pages to [[Category:{CONFLICT_CAT}]]...")
    conflict_cat = site.Pages[f"Category:{CONFLICT_CAT}"]

    for page_name in conflicting_pages:
        try:
            page = site.Pages[page_name]
            text = page.text()

            # Check if already in category
            if f"[[Category:{CONFLICT_CAT}]]" not in text:
                text += f"\n[[Category:{CONFLICT_CAT}]]"
                page.edit(text, "Add page with conflicting Wikidata QIDs")
                print(f"  ✓ {page_name}")
                time.sleep(1.5)
        except Exception as e:
            print(f"  ✗ Error on {page_name}: {e}")

# Write CSV file
print(f"\nWriting CSV file...")
with open('wikidata_qid_duplicates.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Write header
    writer.writerow(['Wikidata QID', 'Number of Pages'] + [f'Page {i+1}' for i in range(max(len(pages) for pages in qid_to_pages.values()))])

    # Sort by number of pages (descending), then by QID
    sorted_qids = sorted(qid_to_pages.items(),
                        key=lambda x: (-len(x[1]), x[0]))

    for qid, page_list in sorted_qids:
        row = [qid, str(len(page_list))] + sorted(page_list)
        writer.writerow(row)

print(f"Wrote CSV with {len(qid_to_pages)} QIDs\n")

# Generate wiki markup for duplicates (QIDs with 2+ pages)
duplicates = {qid: pages for qid, pages in qid_to_pages.items() if len(pages) >= 2}

print(f"Found {len(duplicates)} QIDs with duplicate links\n")

wiki_content = "== Wikidata QID Duplicates ==\n\n"
wiki_content += "This page lists all Wikidata QIDs that are linked from multiple pages in [[Category:Pages linked to Wikidata]].\n\n"
wiki_content += f"Total duplicate QIDs: {len(duplicates)}\n"
wiki_content += f"Total pages with conflicting QIDs: {len(conflicting_pages)}\n\n"

if conflicting_pages:
    wiki_content += "=== Pages with Conflicting QIDs ===\n\n"
    for page_name in sorted(conflicting_pages):
        wiki_content += f"* [[{page_name}]]\n"
    wiki_content += "\n"

# Sort by number of pages (descending)
sorted_duplicates = sorted(duplicates.items(),
                          key=lambda x: (-len(x[1]), x[0]))

wiki_content += "=== Duplicate QIDs ===\n\n"

for qid, page_list in sorted_duplicates:
    wiki_content += f"==== {qid} ====\n"
    wiki_content += f"{{{{wikidata link|{qid}}}}}\n\n"

    for page_name in sorted(page_list):
        wiki_content += f"* [[{page_name}]]\n"

    wiki_content += "\n"

# Write to file
with open('wikidata_qid_duplicates_report.wiki', 'w', encoding='utf-8') as f:
    f.write(wiki_content)

print(f"Wrote wiki report to wikidata_qid_duplicates_report.wiki")

# Upload to wiki
print(f"\nUploading report to [[User:Immanuelle/Wikidata duplicates]]...")
page = site.Pages['User:Immanuelle/Wikidata duplicates']
page.edit(wiki_content, "Update wikidata duplicates report")
print(f"Successfully uploaded!")

print(f"\n=== Summary ===")
print(f"Total pages processed: {len(pages)}")
print(f"Pages with single QID: {sum(len(p) for p in qid_to_pages.values())}")
print(f"Pages with conflicting QIDs: {len(conflicting_pages)}")
print(f"QIDs with duplicates: {len(duplicates)}")
print(f"QIDs total: {len(qid_to_pages)}")
