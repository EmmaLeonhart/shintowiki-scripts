#!/usr/bin/env python3
"""
process_exported_qid_data.py
============================
Process locally downloaded XML exports to find:
1. Pages with duplicate QIDs (multiple pages linking to same QID)
2. Pages with conflicting QIDs (single page with multiple QIDs)
3. Contradictions with the expected CSV mapping (ids and stuff.csv)
"""

import xml.etree.ElementTree as ET
import re
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
EXPORTS_DIR = Path(r'C:\Users\Immanuelle\Downloads\exports')
EXPECTED_CSV = Path(r'C:\Users\Immanuelle\Downloads\ids and stuff.csv')

# ─── HELPERS ─────────────────────────────────────────────────

def extract_all_wikidata_qids(page_text):
    """Extract all unique Wikidata QIDs from page text."""
    matches = re.findall(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    qids = list(set(match[0].upper() for match in matches))  # Get unique QIDs only
    return qids

def load_expected_mapping(csv_file):
    """Load expected QID -> Page mapping from CSV."""
    expected = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                qid = row[0].strip()
                page = row[1].strip()
                expected[page] = qid
    return expected

def parse_export_xml(xml_file):
    """Parse MediaWiki XML export and extract page titles and content."""
    pages = {}
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Handle namespace - try multiple versions
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

print("Loading expected QID mapping...\n")
expected_mapping = load_expected_mapping(EXPECTED_CSV)
print(f"Loaded {len(expected_mapping)} expected QID mappings\n")

# Parse all XML files
print(f"Parsing XML export files...\n")
all_pages = {}
xml_files = sorted(EXPORTS_DIR.glob('export_batch_*.xml'))

for i, xml_file in enumerate(xml_files, 1):
    print(f"Processing {xml_file.name}...")
    pages = parse_export_xml(xml_file)
    all_pages.update(pages)
    print(f"  → {len(pages)} pages, total: {len(all_pages)}\n")

print(f"Total pages loaded: {len(all_pages)}\n")

# Process pages to find issues
print("Analyzing pages for QID issues...\n")

qid_to_pages = defaultdict(list)
conflicting_pages = []
contradictions = []

for page_title, page_text in all_pages.items():
    qids = extract_all_wikidata_qids(page_text)

    # Check for conflicting QIDs (multiple QIDs on same page)
    if len(qids) > 1:
        conflicting_pages.append((page_title, qids))
        print(f"⚠ CONFLICT: {page_title} has multiple QIDs: {qids}")

    # Check for contradictions with expected mapping
    expected_qid = expected_mapping.get(page_title)
    if expected_qid:
        if len(qids) == 0:
            # Expected QID but page has none
            contradictions.append({
                'type': 'missing_qid',
                'page': page_title,
                'expected': expected_qid,
                'actual': None
            })
            print(f"✗ MISSING QID: {page_title} should have {expected_qid} but has none")

        elif expected_qid not in qids:
            # Expected QID doesn't match what's on page
            contradictions.append({
                'type': 'wrong_qid',
                'page': page_title,
                'expected': expected_qid,
                'actual': qids[0] if qids else None
            })
            print(f"✗ WRONG QID: {page_title} should have {expected_qid} but has {qids[0] if qids else 'none'}")

        else:
            # Matches expected
            pass

    # Track all QIDs to pages
    for qid in qids:
        qid_to_pages[qid].append(page_title)

print(f"\nAnalysis complete!\n")

# Find duplicates
duplicates = {qid: pages for qid, pages in qid_to_pages.items() if len(pages) >= 2}

print(f"=== SUMMARY ===")
print(f"Total pages analyzed: {len(all_pages)}")
print(f"Pages with conflicting QIDs: {len(conflicting_pages)}")
print(f"QIDs with contradictions to expected mapping: {sum(1 for c in contradictions if c['type'] == 'wrong_qid')}")
print(f"Pages missing expected QIDs: {sum(1 for c in contradictions if c['type'] == 'missing_qid')}")
print(f"Duplicate QIDs (same QID on multiple pages): {len(duplicates)}\n")

# Write detailed report
print("Writing reports...\n")

# Report 1: Contradictions with expected mapping
with open('contradictions_with_expected.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Type', 'Page', 'Expected QID', 'Actual QID'])

    for contradiction in sorted(contradictions, key=lambda x: x['page']):
        writer.writerow([
            contradiction['type'],
            contradiction['page'],
            contradiction['expected'],
            contradiction['actual'] or ''
        ])

print(f"Wrote {len(contradictions)} contradictions to contradictions_with_expected.csv\n")

# Report 2: Conflicting QIDs (multiple on same page)
with open('conflicting_qids.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Page', 'QIDs Found'])

    for page, qids in sorted(conflicting_pages):
        writer.writerow([page, '|'.join(qids)])

print(f"Wrote {len(conflicting_pages)} pages with conflicting QIDs to conflicting_qids.csv\n")

# Report 3: Duplicate QIDs (same QID on multiple pages)
with open('duplicate_qids.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Find max pages per QID
    max_pages = max(len(pages) for pages in duplicates.values()) if duplicates else 0

    writer.writerow(['QID', 'Count'] + [f'Page {i+1}' for i in range(max_pages)])

    for qid, page_list in sorted(duplicates.items(), key=lambda x: (-len(x[1]), x[0])):
        row = [qid, str(len(page_list))] + sorted(page_list)
        writer.writerow(row)

print(f"Wrote {len(duplicates)} duplicate QIDs to duplicate_qids.csv\n")

# Report 4: Wiki page with all issues
wiki_content = "== Wikidata QID Analysis Report ==\n\n"
wiki_content += f"Report generated from {len(all_pages)} pages\n\n"

wiki_content += f"=== Summary ===\n"
wiki_content += f"* '''Total pages analyzed''': {len(all_pages)}\n"
wiki_content += f"* '''Pages with conflicting QIDs''': {len(conflicting_pages)}\n"
wiki_content += f"* '''Contradictions with expected mapping''': {len(contradictions)}\n"
wiki_content += f"** Wrong QID: {sum(1 for c in contradictions if c['type'] == 'wrong_qid')}\n"
wiki_content += f"** Missing QID: {sum(1 for c in contradictions if c['type'] == 'missing_qid')}\n"
wiki_content += f"* '''QIDs on multiple pages''': {len(duplicates)}\n\n"

if conflicting_pages:
    wiki_content += "=== Pages with Conflicting QIDs ===\n\n"
    for page, qids in sorted(conflicting_pages):
        wiki_content += f"* [[{page}]]: {', '.join(qids)}\n"
    wiki_content += "\n"

if contradictions:
    wiki_content += "=== Contradictions with Expected Mapping ===\n\n"
    for contradiction in sorted(contradictions, key=lambda x: x['page']):
        if contradiction['type'] == 'missing_qid':
            wiki_content += f"* [[{contradiction['page']}]]: Missing {{{{wikidata link|{contradiction['expected']}}}}}\n"
        else:  # wrong_qid
            wiki_content += f"* [[{contradiction['page']}]]: Has {{{{wikidata link|{contradiction['actual']}}}}}, should have {{{{wikidata link|{contradiction['expected']}}}}}\n"
    wiki_content += "\n"

if duplicates:
    wiki_content += "=== Duplicate QIDs ===\n\n"
    for qid, page_list in sorted(duplicates.items(), key=lambda x: (-len(x[1]), x[0]))[:50]:  # Show top 50
        wiki_content += f"* {{{{wikidata link|{qid}}}}}: {', '.join('[[' + p + ']]' for p in sorted(page_list))}\n"
    wiki_content += "\n"

with open('qid_analysis_report.wiki', 'w', encoding='utf-8') as f:
    f.write(wiki_content)

print(f"Wrote wiki report to qid_analysis_report.wiki\n")

print("Done!")
