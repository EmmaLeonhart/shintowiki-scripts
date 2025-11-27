#!/usr/bin/env python3
"""
cleanup_wikidata_generated_pages.py
==================================
Delete pages in [[Category:Wikidata generated shikinaisha pages]]
that do NOT have a {{wikidata link| template.
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

# Get all pages in the category
category = site.Pages['Category:Wikidata generated shikinaisha pages']
pages = list(category)

print(f"Found {len(pages)} pages in category\n")

deleted = 0
kept = 0
failed = 0

for i, page in enumerate(pages, 1):
    try:
        content = page.text()

        # Check if it has {{wikidata link| template
        if re.search(r'\{\{wikidata link\|', content, re.IGNORECASE):
            print(f"{i}. [[{page.name}]] - HAS template, keeping")
            kept += 1
        else:
            print(f"{i}. [[{page.name}]] - NO template, DELETING")
            page.delete("Page does not have wikidata link template")
            deleted += 1

        if i % 10 == 0:
            time.sleep(1)

    except Exception as e:
        print(f"{i}. [[{page.name}]] - ERROR: {e}")
        failed += 1

print(f"\n=== SUMMARY ===")
print(f"Deleted: {deleted}")
print(f"Kept: {kept}")
print(f"Failed: {failed}")
print(f"Total processed: {deleted + kept + failed}")
