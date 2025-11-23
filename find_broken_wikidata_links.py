#!/usr/bin/env python3
"""
find_broken_wikidata_links.py
============================
From wikidata_links_all_pages.csv, find pages that:
1. Do NOT exist in the local XML export, OR
2. Exist in CSV but do NOT have the wikidata link template in the XML
"""

import csv
import re
import sys
import xml.etree.ElementTree as ET
import os
import mwclient
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

print("Logged in to wiki\n")

# Read the ids and stuff CSV
print("Reading ids and stuff.csv...")
pages_to_check = {}  # page_title -> qid

with open(r'C:\Users\Immanuelle\Downloads\ids and stuff.csv', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 2:
            qid = parts[0].strip()
            page = ','.join(parts[1:]).strip()  # In case page title has commas
            # Remove surrounding quotes if present (glitch from CSV parsing)
            if page.startswith('"') and page.endswith('"'):
                page = page[1:-1]
            if page:
                pages_to_check[page] = qid

print(f"Found {len(pages_to_check)} pages in CSV to check\n")

# Parse XML exports and collect all pages with wikidata templates
print("Scanning XML exports for pages with wikidata templates...")
pages_in_xml_with_template = {}  # page_title -> qid

exports_dir = r'C:\Users\Immanuelle\Downloads\exports'
xml_files = sorted([f for f in os.listdir(exports_dir) if f.endswith('.xml')])

for batch_file in xml_files:
    filepath = os.path.join(exports_dir, batch_file)

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        ns = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

        for page in root.findall('.//mw:page', ns):
            title_elem = page.find('mw:title', ns)
            revision = page.find('.//mw:revision', ns)

            if title_elem is not None and revision is not None:
                title = title_elem.text
                text_elem = revision.find('mw:text', ns)

                if text_elem is not None and text_elem.text:
                    content = text_elem.text
                    match = re.search(r'\{\{wikidata link\|([Qq](\d+))\}\}', content)
                    if match:
                        qid = match.group(1).upper()
                        pages_in_xml_with_template[title] = qid

    except Exception as e:
        print(f"Error processing {batch_file}: {e}")

print(f"Found {len(pages_in_xml_with_template)} pages in XML with wikidata templates\n")

# Now find broken links
broken_links = []

print("Finding broken links...")
for title, qid in pages_to_check.items():
    if title not in pages_in_xml_with_template:
        broken_links.append({
            'title': title,
            'qid': qid,
            'status': 'not_in_xml_or_missing_template'
        })

print(f"\nFound {len(broken_links)} broken links\n")

# Create wiki page content
wiki_content = "== Broken Wikidata Links ==\n\n"
wiki_content += f"This page tracks pages from the wikidata CSV that are missing from the XML exports or don't have wikidata link templates.\n\n"
wiki_content += f"'''Total broken links: {len(broken_links)}'''\n\n"

wiki_content += "{| class=\"wikitable sortable\"\n"
wiki_content += "|-\n"
wiki_content += "! # !! Page !! QID\n"
for i, item in enumerate(broken_links, 1):
    wiki_content += f"|-\n| {i} || [[{item['title']}]] || {{{{q|{item['qid']}}}}}\n"
wiki_content += "|}\n"

# Upload to wiki
print(f"Uploading to [[User:Immanuelle/Broken wikidata links]]...\n")
page = site.Pages['User:Immanuelle/Broken wikidata links']
page.edit(wiki_content, "Create broken wikidata links report")

print("Done!")
