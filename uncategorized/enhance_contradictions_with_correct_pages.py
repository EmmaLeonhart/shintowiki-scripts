#!/usr/bin/env python3
"""
enhance_contradictions_with_correct_pages.py
==============================================
For each contradiction, find which page actually has the expected QID
"""

import csv
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path
from collections import defaultdict

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
EXPORTS_DIR = Path(r'C:\Users\Immanuelle\Downloads\exports')

# ─── HELPERS ─────────────────────────────────────────────────

def extract_all_wikidata_qids(page_text):
    """Extract all unique Wikidata QIDs from page text."""
    matches = re.findall(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    qids = list(set(match[0].upper() for match in matches))
    return qids

def parse_export_xml(xml_file):
    """Parse MediaWiki XML export and extract page titles and content."""
    pages = {}
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Handle namespace
        ns = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

        for page_elem in root.findall('.//mw:page', ns):
            title_elem = page_elem.find('mw:title', ns)
            text_elem = page_elem.find('.//mw:text', ns)

            if title_elem is not None and text_elem is not None:
                title = title_elem.text
                text = text_elem.text or ''
                if title:
                    pages[title] = text

    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")

    return pages

# ─── MAIN LOGIC ──────────────────────────────────────────────

print("Reading contradictions...\n")
contradictions = []
with open('contradictions_with_expected.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        contradictions.append(row)

print(f"Read {len(contradictions)} contradictions\n")

# Extract unique expected QIDs to search for
expected_qids = set(c['Expected QID'] for c in contradictions)
print(f"Searching for {len(expected_qids)} unique expected QIDs\n")

# Parse all XML files and build QID -> Pages mapping
print("Parsing XML files to find pages with expected QIDs...\n")
qid_to_pages = defaultdict(list)
xml_files = sorted(EXPORTS_DIR.glob('export_batch_*.xml'))

for i, xml_file in enumerate(xml_files, 1):
    if i % 5 == 0:
        print(f"Processing {xml_file.name}...")

    pages = parse_export_xml(xml_file)

    for page_title, page_text in pages.items():
        qids = extract_all_wikidata_qids(page_text)

        # Track which pages have the expected QIDs
        for qid in qids:
            if qid in expected_qids:
                qid_to_pages[qid].append(page_title)

print(f"\nBuilt mapping of QIDs to pages\n")

# Update contradictions with the page that has the expected QID
print("Updating contradictions with correct pages...\n")

for contradiction in contradictions:
    expected_qid = contradiction['Expected QID']
    pages_with_expected = qid_to_pages.get(expected_qid, [])

    # Filter out the page with wrong QID
    wrong_page = contradiction['Page']
    correct_pages = [p for p in pages_with_expected if p != wrong_page]

    if correct_pages:
        # Use the first correct page (or the most likely one)
        # If there are multiple, show all
        contradiction['Correct Page'] = '|'.join(correct_pages)
        print(f"✓ {wrong_page}: Expected {expected_qid} is on {', '.join(correct_pages)}")
    else:
        contradiction['Correct Page'] = 'NOT FOUND'
        print(f"✗ {wrong_page}: Expected {expected_qid} not found on any page!")

# Write enhanced CSV
print("\nWriting enhanced contradictions CSV...\n")
with open('contradictions_with_expected_enhanced.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Type', 'Page', 'Expected QID', 'Actual QID', 'Correct Page'])
    writer.writeheader()
    writer.writerows(contradictions)

print("Wrote contradictions_with_expected_enhanced.csv\n")

# Count results
found = sum(1 for c in contradictions if c['Correct Page'] != 'NOT FOUND')
not_found = sum(1 for c in contradictions if c['Correct Page'] == 'NOT FOUND')

print(f"=== Summary ===")
print(f"Contradictions with correct page found: {found}/{len(contradictions)}")
print(f"Contradictions where correct page not found: {not_found}/{len(contradictions)}")
