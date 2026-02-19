"""generate_quickstatements_wikidata_links.py
================================================
Generate QuickStatements for pages with wikidata links that haven't been categorized yet.

This script:
1. Gets all pages in [[Category:Pages linked to Wikidata]]
2. Excludes pages already in "Matching pagename on wikidata" or "Non matching pagename on wikidata"
3. For each remaining page, extracts {{wikidata link|Q...}}
4. Generates QuickStatements: Q12345|P11250|"Page Name"
================================================
"""

import mwclient
import requests
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

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    # Try to find {{wikidata link|Q...}}
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Try to find [[wikidata:Q...]]
    match = re.search(r'\[\[wikidata:([Qq](\d+))\]\]', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def has_category(page_text, category_name):
    """Check if a page already has a category."""
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]'
    return bool(re.search(pattern, page_text, re.IGNORECASE))


def main():
    """Generate QuickStatements for uncategorized wikidata links."""

    print("Generating QuickStatements for uncategorized Wikidata links")
    print("=" * 60)

    # Get all pages in Pages linked to Wikidata category
    print("\nFetching mainspace pages in [[Category:Pages linked to Wikidata]]...")
    category = site.pages['Category:Pages linked to Wikidata']

    try:
        all_members = list(category.members())
        # Filter to mainspace only (namespace 0)
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")
    print(f"Filtering for uncategorized pages...\n")

    quickstatements = []
    processed_count = 0
    skipped_already_categorized = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name

            # Get page text
            text = page.text()

            # Check if already categorized (matching or non-matching)
            if has_category(text, "Matching pagename on wikidata") or has_category(text, "Non matching pagename on wikidata"):
                skipped_already_categorized += 1
                continue

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                continue

            # Generate QuickStatement
            quickstatement = f'{qid}|P11250|"{page_name}"'
            quickstatements.append(quickstatement)
            processed_count += 1

            if processed_count % 100 == 0:
                print(f"  Processed {processed_count} pages...")

        except Exception as e:
            try:
                pass  # Silent skip on errors
            except:
                pass

        # Rate limiting
        time.sleep(0.1)

    # Save to file
    output_file = 'wikidata_links_quickstatements.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for statement in quickstatements:
            f.write(statement + '\n')

    print(f"\n{'=' * 60}")
    print(f"QuickStatements saved to: {output_file}")
    print(f"Total statements generated: {len(quickstatements)}")
    print(f"Pages with uncategorized wikidata: {processed_count}")
    print(f"Pages skipped (already categorized): {skipped_already_categorized}")


if __name__ == "__main__":
    main()
