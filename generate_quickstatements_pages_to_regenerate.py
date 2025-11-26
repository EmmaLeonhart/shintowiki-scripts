"""generate_quickstatements_pages_to_regenerate.py
================================================
Generate QuickStatements for pages in [[Category:Pages to be regenerated]].

This script:
1. Gets all pages in [[Category:Pages to be regenerated]]
2. For each page, extracts {{wikidata link|Q...}}
3. Generates QuickStatements: Q12345|P11250|"Page Name"
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


def main():
    """Generate QuickStatements for pages to be regenerated."""

    print("Generating QuickStatements for pages in [[Category:Pages to be regenerated]]")
    print("=" * 60)

    # Get all pages in Pages to be regenerated category
    print("\nFetching mainspace pages in [[Category:Pages to be regenerated]]...")
    category = site.pages['Category:Pages to be regenerated']

    try:
        all_members = list(category.members())
        # Filter to mainspace only (namespace 0)
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")

    quickstatements = []
    processed_count = 0
    no_wikidata_found = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                no_wikidata_found += 1
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
    output_file = 'wikidata_links_pages_to_regenerate_quickstatements.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for statement in quickstatements:
            f.write(statement + '\n')

    print(f"\n{'=' * 60}")
    print(f"QuickStatements saved to: {output_file}")
    print(f"Total statements generated: {len(quickstatements)}")
    print(f"Pages with wikidata links: {processed_count}")
    print(f"Pages without wikidata links: {no_wikidata_found}")


if __name__ == "__main__":
    main()
