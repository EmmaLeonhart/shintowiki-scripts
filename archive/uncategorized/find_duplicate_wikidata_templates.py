#!/usr/bin/env python3
"""
find_duplicate_wikidata_templates.py
===================================
Scan XML exports to find all pages with multiple {{wikidata link|QID}} templates.
"""

import xml.etree.ElementTree as ET
import re
import os

exports_dir = r'C:\Users\Immanuelle\Downloads\exports'
output_file = r'C:\Users\Immanuelle\Downloads\exports\duplicate_wikidata_from_xml.txt'

# Find all XML files
xml_files = sorted([f for f in os.listdir(exports_dir) if f.endswith('.xml')])
print(f"Found {len(xml_files)} XML files\n")

pages_with_duplicates = []

for batch_file in xml_files:
    filepath = os.path.join(exports_dir, batch_file)
    print(f"Processing {batch_file}...")

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Define namespace
        ns = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

        # Find all pages
        for page in root.findall('.//mw:page', ns):
            title_elem = page.find('mw:title', ns)
            revision = page.find('.//mw:revision', ns)

            if title_elem is not None and revision is not None:
                title = title_elem.text
                text_elem = revision.find('mw:text', ns)

                if text_elem is not None and text_elem.text:
                    content = text_elem.text

                    # Find all wikidata link templates
                    matches = re.findall(r'\{\{wikidata link\|([Qq]\d+)\}\}', content)

                    # If more than one, record it
                    if len(matches) > 1:
                        pages_with_duplicates.append((title, len(matches)))

    except Exception as e:
        print(f"  ERROR processing {batch_file}: {e}")

print(f"\nFound {len(pages_with_duplicates)} pages with duplicate wikidata templates")

# Write to file
with open(output_file, 'w', encoding='utf-8') as f:
    for title, count in pages_with_duplicates:
        f.write(f"{title}|{count}\n")

print(f"Written to {output_file}")
