#!/usr/bin/env python3
"""
create_qid_redirects_to_pages.py
================================
For each page in [[Category:Pages linked to Wikidata]]:
1. Extract the QID from {{wikidata link|QXXXXX}}
2. Create/overwrite a page at the QID name with: #redirect[[Page Name]]
This makes QID pages redirect to their respective shrine pages
"""

import mwclient
import sys
import time
import re

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API)\n")

print("Processing pages in [[Category:Pages linked to Wikidata]]...\n")
print("=" * 60)

category = site.pages['Category:Pages linked to Wikidata']
all_members = list(category.members())
members = [m for m in all_members if m.namespace == 0]  # mainspace only

print(f"Found {len(members)} mainspace pages\n")

processed_count = 0
error_count = 0
no_qid_count = 0

for i, page in enumerate(members, 1):
    page_name = page.name

    try:
        page_text = page.text()
    except Exception as e:
        print(f"{i:4d}. {page_name:50s} [ERROR reading: {str(e)[:40]}]")
        error_count += 1
        continue

    # Extract QID from {{wikidata link|QXXXXX}}
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if not match:
        print(f"{i:4d}. {page_name:50s} [NO QID FOUND]")
        no_qid_count += 1
        continue

    qid = match.group(1).upper()

    try:
        # Create/overwrite QID page with redirect to the page name
        redirect_content = f"#redirect[[{page_name}]]"

        qid_page = site.pages[qid]
        qid_page.edit(redirect_content, summary="v25: QID redirects to page")

        print(f"{i:4d}. {page_name:50s} ({qid}) ... ✓")
        processed_count += 1
        time.sleep(1.0)

    except Exception as e:
        print(f"{i:4d}. {page_name:50s} ({qid}) ... ! ERROR: {str(e)[:40]}")
        error_count += 1
        time.sleep(0.5)

print(f"\n{'=' * 60}")
print(f"Summary:")
print(f"  Total pages: {len(members)}")
print(f"  QID redirects created: {processed_count}")
print(f"  Pages without QID: {no_qid_count}")
print(f"  Errors: {error_count}")
