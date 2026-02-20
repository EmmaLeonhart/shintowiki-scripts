#!/usr/bin/env python3
"""
upload_wikidata_duplicates_page.py
===================================
Upload the wikidata duplicates page to [[User:Immanuelle/Wikidata duplicates]]
"""

import mwclient
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
PAGE_NAME = 'User:Immanuelle/Wikidata duplicates'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Read the duplicates page content
with open('Wikidata_duplicates_page.wiki', 'r', encoding='utf-8') as f:
    page_content = f.read()

print(f"Read {len(page_content)} characters from Wikidata_duplicates_page.wiki")
print(f"Uploading to [[{PAGE_NAME}]]...\n")

# Get the page
page = site.Pages[PAGE_NAME]

# Check if page exists and what it currently contains
try:
    current_text = page.text()
    print(f"Page exists with {len(current_text)} characters")
    if current_text == page_content:
        print("Page content is identical - no update needed")
        sys.exit(0)
    else:
        print("Page content differs - updating...")
except:
    print("Page doesn't exist - creating...")

# Upload the page
page.edit(page_content, "Update wikidata duplicates list")

print(f"Successfully uploaded to [[{PAGE_NAME}]]")
time.sleep(1.5)
