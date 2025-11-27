#!/usr/bin/env python3
"""
create_qid_redirects.py
=======================
Creates redirect pages from Wikidata QIDs to actual page names.

For each page in [[Category:Pages linked to Wikidata]]:
1. Extract the {{wikidata link|QXXXXXX}} template
2. Create a page named [[QXXXXXX]] that redirects to the actual page
3. Add [[Category:QID redirects]] to the redirect page
4. Overwrites any existing content on the QID page
"""

import mwclient
import sys
import time
import re

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

# Get the category
category = site.pages['Category:Pages linked to Wikidata']

print("Fetching pages in [[Category:Pages linked to Wikidata]]...")
try:
    members = list(category.members())
except Exception as e:
    print(f"ERROR: Could not fetch category members – {e}")
    sys.exit(1)

print(f"Found {len(members)} pages\n")
print("Processing pages...\n")

redirect_created = 0
no_wikidata_found = 0
error_count = 0

for i, page in enumerate(members, 1):
    try:
        page_name = page.name
        print(f"{i}. [[{page_name}]]", end="", flush=True)

        # Get page content
        text = page.text()

        # Extract wikidata link using regex - looking for {{wikidata link|QXXXXXX}}
        wikidata_pattern = r'\{\{wikidata link\|([Qq]\d+)\}\}'
        match = re.search(wikidata_pattern, text)

        if not match:
            print(f" ... • No wikidata link found")
            no_wikidata_found += 1
            continue

        qid = match.group(1).upper()  # Normalize to uppercase

        # Create redirect content
        redirect_content = f"#redirect[[{page_name}]]\n[[Category:QID redirects]]\n"

        # Get or create the QID page and overwrite it
        try:
            qid_page = site.pages[qid]
            qid_page.save(redirect_content, "Bot: create QID redirect")
            print(f" ... ✓ Created redirect {qid} → {page_name}")
            redirect_created += 1
        except Exception as e:
            print(f" ... ! Error saving QID page: {str(e)[:60]}")
            continue

        time.sleep(1.5)

    except Exception as e:
        try:
            print(f"\n   ! ERROR: {str(e)[:80]}")
        except UnicodeEncodeError:
            print(f"\n   ! ERROR: {e}")
        error_count += 1

print(f"\n{'=' * 60}")
print(f"\nSummary:")
print(f"  Total pages: {len(members)}")
print(f"  Redirects created: {redirect_created}")
print(f"  No wikidata link found: {no_wikidata_found}")
print(f"  Errors: {error_count}")
