#!/usr/bin/env python3
"""
recover_overwritten_final.py
============================
Recover accidentally overwritten pages from edit history.

Processes multiple categories:
1. [[Category:Accidentally overwritten pages]]
2. [[Category:Pages that were shrank]]
3. [[Category:Pages_likely_having_an_accidental_overwite_in_their_history_that_shrank_them]]

For each page:
1. Check edit history (search deeply)
2. Find edits with "Create shrine page for" in the summary
3. If found, append the previous content to the current page
   under an "Accidentally Overwritten Content" section
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

# Categories to process
categories_to_process = [
    'Category:Accidentally overwritten pages',
    'Category:Pages that were shrank',
    'Category:Pages_likely_having_an_accidental_overwite_in_their_history_that_shrank_them'
]

total_recovered = 0
total_no_overwrite = 0
total_no_prev_revision = 0
total_errors = 0
total_pages = 0

for category_name in categories_to_process:
    print(f"\n{'=' * 60}")
    print(f"Processing [[{category_name}]]...")
    print(f"{'=' * 60}\n")

    try:
        category = site.pages[category_name]
        members = list(category.members())
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        continue

    print(f"Found {len(members)} pages\n")

    recovered_count = 0
    no_overwrite_found = 0
    no_previous_revision = 0
    error_count = 0

    for i, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{i}. [[{page_name}]]", end="", flush=True)

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

            # Get the content of the previous revision using ONLY revids
            try:
                prev_revid = previous_revision.get('revid')

                # Fetch old content - use revids parameter alone
                prev_text = site.api('query', revids=prev_revid, prop='revisions', rvprop='content')

                revisions_data = []
                for page_data in prev_text.get('query', {}).get('pages', {}).values():
                    revisions_data.extend(page_data.get('revisions', []))

                if not revisions_data:
                    print(f" ... • Could not fetch previous revision content")
                    continue

                prev_content = revisions_data[0].get('*', '')

                # Get current page content
                current_text = page.text()

                # Build the recovery section
                recovery_section = "\n\n== Accidentally Overwritten Content ==\n"
                recovery_section += prev_content

                # Append to current page
                new_text = current_text + recovery_section

                # Save the page
                page.save(new_text, "Bot: recover accidentally overwritten content")

                print(f" ... ✓ Recovered")
                recovered_count += 1

            except Exception as e:
                print(f" ... ! Error: {str(e)[:60]}")
                continue

            time.sleep(1.5)

        except Exception as e:
            print(f"\n   ! ERROR: {str(e)[:80]}")
            error_count += 1

    print(f"\n{'-' * 60}")
    print(f"Category Summary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Recovered: {recovered_count}")
    print(f"  No overwrite found: {no_overwrite_found}")
    print(f"  No previous revision: {no_previous_revision}")
    print(f"  Errors: {error_count}")

    total_recovered += recovered_count
    total_no_overwrite += no_overwrite_found
    total_no_prev_revision += no_previous_revision
    total_errors += error_count
    total_pages += len(members)

print(f"\n{'=' * 60}")
print(f"OVERALL SUMMARY:")
print(f"{'=' * 60}")
print(f"  Total pages processed: {total_pages}")
print(f"  Total recovered: {total_recovered}")
print(f"  Total no overwrite found: {total_no_overwrite}")
print(f"  Total no previous revision: {total_no_prev_revision}")
print(f"  Total errors: {total_errors}")
