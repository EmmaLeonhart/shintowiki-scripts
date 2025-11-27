#!/usr/bin/env python3
"""
upload_qid_analysis_report.py
==============================
Upload the QID analysis report to [[User:Immanuelle/Wikidata duplicates]]
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

# Read the report
with open('qid_analysis_report.wiki', 'r', encoding='utf-8') as f:
    page_content = f.read()

print(f"Read {len(page_content)} characters from report\n")
print(f"Uploading to [[{PAGE_NAME}]]...\n")

# Edit the page
page = site.Pages[PAGE_NAME]
page.edit(page_content, "Update wikidata QID duplicates analysis report")

print(f"Successfully uploaded!\n")
time.sleep(1.5)

print("Done!")
