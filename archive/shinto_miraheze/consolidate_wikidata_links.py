#!/usr/bin/env python3
"""
consolidate_wikidata_links.py
============================
Remove all duplicate {{wikidata link|QID}} templates from pages and append single one at end.
Reads list of pages with duplicates from local XML file.
"""

import mwclient
import re
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

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Read the list of pages with duplicates
pages_to_fix = []
duplicate_file = r'C:\Users\Immanuelle\Downloads\exports\duplicate_wikidata_from_xml.txt'

with open(duplicate_file, 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if parts and parts[0]:
            pages_to_fix.append({
                'title': parts[0],
                'count': int(parts[1]) if len(parts) > 1 else 0
            })

print(f"Will fix {len(pages_to_fix)} pages with duplicate wikidata link templates\n")

fixed = 0
failed = 0
skipped = 0

for i, page_data in enumerate(pages_to_fix, 1):
    title = page_data['title']

    try:
        page = site.Pages[title]
        content = page.text()

        # Find all wikidata link templates
        matches = re.findall(r'\{\{wikidata link\|([Qq]\d+)\}\}', content)

        if len(matches) > 1:
            # Get the QID (should be same for all matches)
            qid = matches[0].upper()

            # Remove all wikidata link templates
            new_content = re.sub(r'\{\{wikidata link\|[Qq]\d+\}\}\n?', '', content)

            # Add one at the end
            new_content = new_content.rstrip() + f"\n{{{{wikidata link|{qid}}}}}"

            # Edit the page
            page.edit(new_content, "Consolidate multiple wikidata link templates into single one at end")

            print(f"{i}. [[{title}]] - consolidated {len(matches)} templates")
            fixed += 1
        else:
            skipped += 1

        if i % 10 == 0:
            time.sleep(1)

    except Exception as e:
        print(f"{i}. [[{title}]] - ERROR: {e}")
        failed += 1

print(f"\n=== SUMMARY ===")
print(f"Fixed: {fixed}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")
print(f"Total processed: {fixed + skipped + failed}")
