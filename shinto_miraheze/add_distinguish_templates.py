#!/usr/bin/env python3
"""
add_distinguish_templates.py
============================
For each page in [[Category:Pages created to resolve qid conflicts (not on wikidata)]]
Extract the QID from the title and add a distinguish template to the main page
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
CATEGORY  = 'Pages created to resolve qid conflicts (not on wikidata)'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Get all pages in category
print(f"Fetching pages from [[Category:{CATEGORY}]]...\n")

category = site.Categories[CATEGORY]
pages = list(category)

print(f"Found {len(pages)} pages\n")

# Process each page
successful = 0
failed = 0

for i, page in enumerate(pages, 1):
    page_title = page.name

    # Extract the QID from the page title (e.g., "Futsuno Shrine (Q135041412)" -> "Q135041412")
    match = re.search(r'\(([Qq]\d+)\)$', page_title)
    if not match:
        print(f"{i}. Skipping [[{page_title}]] - no QID found in title\n")
        continue

    qid = match.group(1)
    # Extract the base page name without the QID
    base_page_name = page_title[:match.start()].strip()

    print(f"{i}. Processing [[{page_title}]]...")
    print(f"   Base page: [[{base_page_name}]], QID: {qid}\n")

    try:
        # Get the main page (without QID)
        main_page = site.Pages[base_page_name]
        main_content = main_page.text()

        # Create distinguish template
        distinguish_template = f"{{{{distinguish|{page_title}}}}}\n\n"

        # Check if distinguish template already exists
        if f"{{{{distinguish|{page_title}}}}}" in main_content:
            print(f"   ⊘ Distinguish template already exists\n")
            continue

        # Add distinguish template at the beginning
        new_content = distinguish_template + main_content

        # Edit the page
        main_page.edit(new_content, f"Add distinguish template for [[{page_title}]]")

        print(f"   ✓ Added distinguish template to [[{base_page_name}]]\n")
        successful += 1

    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        failed += 1

    time.sleep(1.5)

print(f"\n=== Summary ===")
print(f"Successfully updated: {successful}/{len(pages)}")
print(f"Failed: {failed}/{len(pages)}")
