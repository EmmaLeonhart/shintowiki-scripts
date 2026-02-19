#!/usr/bin/env python3
"""
recover_shrunk_pages.py
=======================
Recover accidentally shrunk pages from edit history.

For each page in [[Category:Pages that were shrank]]:
1. Check edit history (search deeply)
2. Find edits with "Create shrine page for" in the summary
3. If found, append the previous content to the current page
   under an "Accidentally Overwritten Content" section
4. Handles cases where there's no previous revision gracefully
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

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# Get the category
category = site.pages['Category:Pages that were shrank']

print("Fetching pages in [[Category:Pages that were shrank]]...")
try:
    members = list(category.members())
except Exception as e:
    print(f"ERROR: Could not fetch category members – {e}")
    sys.exit(1)

print(f"Found {len(members)} pages\n")
print("Processing pages...\n")

recovered_count = 0
no_overwrite_found = 0
no_previous_revision = 0
error_count = 0

for i, page in enumerate(members, 1):
    try:
        page_name = page.name
        print(f"{i}. [[{page_name}]]", end="")
        sys.stdout.flush()

        # Get page history (search deeply - limit 500)
        revisions = list(page.revisions(dir='older', limit=500))

        # Look for the "Create shrine page for" edit
        overwrite_revision = None
        previous_revision = None

        for j, rev in enumerate(revisions):
            comment = rev.get('comment', '')
            if 'Create shrine page for' in comment:
                overwrite_revision = rev
                # The previous revision is the next one in the list (since dir='older')
                if j + 1 < len(revisions):
                    previous_revision = revisions[j + 1]
                break

        if not overwrite_revision:
            print(f" ... • No overwrite edit found")
            no_overwrite_found += 1
            continue

        if not previous_revision:
            print(f" ... • Found overwrite but no previous revision")
            no_previous_revision += 1
            continue

        # Get the content of the previous revision
        try:
            # Fetch old content using revids parameter alone
            prev_text = site.api('query', revids=previous_revision['revid'],
                                rvprop='content')

            if 'query' not in prev_text or 'badrevids' in prev_text['query']:
                print(f" ... • Could not fetch previous revision content")
                continue

            revisions_data = []
            for page_data in prev_text['query'].get('pages', {}).values():
                revisions_data.extend(page_data.get('revisions', []))

            if not revisions_data:
                print(f" ... • Could not fetch previous revision content")
                continue

            prev_content = revisions_data[0]['*']

            # Get current page content
            current_text = page.text()

            # Build the recovery section
            recovery_section = "\n\n== Accidentally Overwritten Content ==\n"
            recovery_section += prev_content

            # Append to current page
            new_text = current_text + recovery_section

            # Save the page
            page.save(new_text, "Bot: recover accidentally overwritten content")

            print(f" ... ✓ Recovered content from revision {previous_revision['revid']}")
            recovered_count += 1

        except Exception as e:
            print(f" ... ! Error recovering: {e}")
            continue

        time.sleep(1.5)

    except Exception as e:
        try:
            print(f"\n   ! ERROR: {e}")
        except UnicodeEncodeError:
            print(f"\n   ! ERROR: {str(e)}")
        error_count += 1

print(f"\n{'=' * 60}")
print(f"\nSummary:")
print(f"  Total pages: {len(members)}")
print(f"  Recovered: {recovered_count}")
print(f"  No overwrite found: {no_overwrite_found}")
print(f"  Found overwrite but no previous revision: {no_previous_revision}")
print(f"  Errors: {error_count}")
