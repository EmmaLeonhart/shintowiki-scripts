#!/usr/bin/env python3
"""
reorganize_categories.py
=========================
Reorganizes categories on pages in [[Category:Pages linked to Wikidata]].

For each page:
1. Extract all categories from the page
2. Remove duplicates
3. Sort alphabetically
4. Move all categories to the bottom of the page
5. Save the page

Categories are identified by [[Category:...]] links.
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

reorganized_count = 0
no_change_count = 0
error_count = 0

for i, page in enumerate(members, 1):
    try:
        page_name = page.name
        print(f"{i}. [[{page_name}]]", end="", flush=True)

        # Get page content
        text = page.text()

        # Extract all categories using regex
        category_pattern = r'\[\[Category:([^\]]+)\]\]'
        categories = re.findall(category_pattern, text)

        if not categories:
            print(f" ... • No categories found")
            no_change_count += 1
            continue

        # Remove duplicates and sort alphabetically
        unique_categories = sorted(set(categories), key=str.lower)

        # Remove all category links from the text
        text_without_categories = re.sub(category_pattern, '', text)

        # Remove trailing whitespace (blank lines at end)
        text_without_categories = text_without_categories.rstrip()

        # Build the new categories section
        categories_section = '\n'
        for cat in unique_categories:
            categories_section += f'[[Category:{cat}]]\n'

        # Combine text with categories at the bottom
        new_text = text_without_categories + categories_section

        # Check if text actually changed
        if new_text.strip() == text.strip():
            print(f" ... • Already organized")
            no_change_count += 1
            continue

        # Save the page
        page.save(new_text, "Bot: reorganize categories (alphabetical, deduplicated, moved to bottom)")

        print(f" ... ✓ Reorganized ({len(unique_categories)} categories)")
        reorganized_count += 1

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
print(f"  Reorganized: {reorganized_count}")
print(f"  Already organized: {no_change_count}")
print(f"  Errors: {error_count}")
