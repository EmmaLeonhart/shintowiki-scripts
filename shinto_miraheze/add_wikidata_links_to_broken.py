#!/usr/bin/env python3
"""
add_wikidata_links_to_broken.py
==============================
Add {{wikidata link|QID}} template to the bottom of all pages listed in
[[User:Immanuelle/Broken wikidata links]]
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

print("Logged in to wiki\n")

# Get the broken wikidata links page to extract page/QID pairs
print("Reading [[User:Immanuelle/Broken wikidata links]]...")
broken_page = site.Pages['User:Immanuelle/Broken wikidata links']
page_content = broken_page.text()

# Parse the table to extract page titles and QIDs
pages_to_fix = []
# Match rows like: | 1 || [[Pagename]] || {{q|QXXXXXXX}}
pattern = r'\|\s*\d+\s*\|\|\s*\[\[([^\]]+)\]\]\s*\|\|\s*\{\{q\|([Qq]\d+)\}\}'
for match in re.finditer(pattern, page_content):
    page_title = match.group(1)
    qid = match.group(2).upper()
    pages_to_fix.append({'title': page_title, 'qid': qid})

print(f"Found {len(pages_to_fix)} pages to fix\n")

# Now add the wikidata link template to each page
added = 0
failed = 0

for i, page_data in enumerate(pages_to_fix, 1):
    title = page_data['title']
    qid = page_data['qid']

    try:
        page = site.Pages[title]
        content = page.text()

        # Check if it already has a wikidata link template
        if re.search(r'\{\{wikidata link\|', content, re.IGNORECASE):
            print(f"{i}. [[{title}]] - already has wikidata link, skipping")
            continue

        # Add the template to the bottom
        new_content = content.rstrip() + f"\n{{{{wikidata link|{qid}}}}}"

        # Edit the page
        page.edit(new_content, f"Add wikidata link template for {qid}")

        print(f"{i}. [[{title}]] - added {{{{wikidata link|{qid}}}}}")
        added += 1

        if i % 10 == 0:
            time.sleep(1)

    except Exception as e:
        print(f"{i}. [[{title}]] - ERROR: {e}")
        failed += 1

print(f"\n=== SUMMARY ===")
print(f"Added: {added}")
print(f"Failed: {failed}")
print(f"Skipped (already had template): {len(pages_to_fix) - added - failed}")
print(f"Total processed: {added + failed + (len(pages_to_fix) - added - failed)}")
