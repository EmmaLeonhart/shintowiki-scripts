#!/usr/bin/env python3
"""
find_wikidata_qid_duplicates_bulk.py
====================================
Use bulk export to get all pages from [[Category:Pages linked to Wikidata]] at once,
then process them locally to find QID duplicates and conflicting pages.
"""

import mwclient
import re
import sys
import time
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from io import StringIO

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

print(f"Fetching category members from [[Category:{CATEGORY}]]...\n")

# Get all pages in the category
category = site.Categories[CATEGORY]
pages_list = list(category)

print(f"Found {len(pages_list)} pages\n")

# Get page names for export
page_names = [p.name for p in pages_list]

# Export pages in chunks (MediaWiki has limits on export size)
chunk_size = 500
pages_data = {}

print(f"Exporting pages in chunks of {chunk_size}...\n")

for chunk_num, i in enumerate(range(0, len(page_names), chunk_size), 1):
    chunk = page_names[i:i+chunk_size]
    print(f"Exporting chunk {chunk_num} ({i+1}-{min(i+chunk_size, len(page_names))})...")

    try:
        # Use the export API to get XML
        params = {
            'action': 'query',
            'titles': '|'.join(chunk),
            'export': True,
            'exportnowrap': True,
            'format': 'json'
        }

        response = site.api(**params)

        # Parse the XML response
        if 'export' in response:
            export_xml = response['export']['*']

            # Parse XML
            root = ET.fromstring(export_xml)

            # Extract page content
            ns = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
            for page_elem in root.findall('mw:page', ns):
                title_elem = page_elem.find('mw:title', ns)
                text_elem = page_elem.find('mw:revision/mw:text', ns)

                if title_elem is not None and text_elem is not None:
                    title = title_elem.text
                    text = text_elem.text or ''
                    pages_data[title] = text

    except Exception as e:
        print(f"  Error exporting chunk: {e}")
        # Fallback to individual fetches for this chunk
        for page_name in chunk:
            try:
                page = site.Pages[page_name]
                pages_data[page_name] = page.text()
            except Exception as e2:
                print(f"    Error fetching {page_name}: {e2}")

    time.sleep(1)

print(f"\nSuccessfully loaded {len(pages_data)} pages\n")

# Process pages locally
print("Processing pages for QID duplicates...\n")

qid_to_pages = defaultdict(list)
conflicting_pages = []

for i, (page_name, text) in enumerate(pages_data.items(), 1):
    if i % 500 == 0:
        print(f"Processing page {i}/{len(pages_data)}...")

    qids = extract_all_wikidata_qids(text)

    if len(qids) > 1:
        # Page has conflicting QIDs
        conflicting_pages.append(page_name)
    elif len(qids) == 1:
        # Single QID - add to mapping
        qid_to_pages[qids[0]].append(page_name)

print(f"\nFound {len(conflicting_pages)} pages with conflicting QIDs")

# Add conflicting pages to category
if conflicting_pages:
    print(f"\nAdding {len(conflicting_pages)} conflicting pages to [[Category:{CONFLICT_CAT}]]...")
    for idx, page_name in enumerate(conflicting_pages, 1):
        if idx % 50 == 0:
            print(f"  Processing {idx}/{len(conflicting_pages)}...")

        try:
            page = site.Pages[page_name]
            text = page.text()

            # Check if already in category
            if f"[[Category:{CONFLICT_CAT}]]" not in text:
                text += f"\n[[Category:{CONFLICT_CAT}]]"
                page.edit(text, "Add page with conflicting Wikidata QIDs")

            time.sleep(1.5)
        except Exception as e:
            print(f"  Error on {page_name}: {e}")

# Write CSV file
print(f"\nWriting CSV file...")
with open('wikidata_qid_duplicates.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Find max number of pages for any QID
    max_pages = max(len(pages) for pages in qid_to_pages.values()) if qid_to_pages else 0

    # Write header
    writer.writerow(['Wikidata QID', 'Number of Pages'] + [f'Page {i+1}' for i in range(max_pages)])

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
    wiki_content += f"==== {qid} ({len(page_list)} pages) ====\n"
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
print(f"Total pages processed: {len(pages_data)}")
print(f"Pages with single QID: {sum(len(p) for p in qid_to_pages.values())}")
print(f"Pages with conflicting QIDs: {len(conflicting_pages)}")
print(f"QIDs with duplicates: {len(duplicates)}")
print(f"QIDs total: {len(qid_to_pages)}")
