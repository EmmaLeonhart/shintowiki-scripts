"""extract_ancient_egyptian_decans_wikidata.py
================================================
Extract Wikidata QIDs for all members of [[Category:Ancient Egyptian Decans]]
================================================

This script:
1. Fetches all pages in [[Category:Ancient Egyptian Decans]]
2. Extracts the Wikidata QID from each page
3. Creates a CSV with Page Name and QID
"""

import mwclient
import sys
import csv
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

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text.

    Looks for patterns like:
    {{wikidata link|Q12345}}
    [[wikidata:Q12345]]
    """
    # Try to find {{wikidata link|Q...}}
    match = re.search(r'{{wikidata link\|([Qq]\d+)}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Try to find [[wikidata:Q...]]
    match = re.search(r'\[\[wikidata:([Qq]\d+)\]\]', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def main():
    """Extract Wikidata for all Ancient Egyptian Decans members."""

    print("Extracting Wikidata QIDs for Ancient Egyptian Decans\n")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Ancient Egyptian Decans']

    print(f"\nFetching all pages in [[Category:Ancient Egyptian Decans]]...")
    try:
        members = list(category.members())
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} members\n")

    results = []
    found_count = 0
    not_found_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end=" ... ")

            text = page.text()
            qid = extract_wikidata_qid(text)

            if qid:
                print(f"✓ {qid}")
                results.append({
                    'Page Name': page_name,
                    'Wikidata QID': qid
                })
                found_count += 1
            else:
                print(f"• No QID")
                results.append({
                    'Page Name': page_name,
                    'Wikidata QID': ''
                })
                not_found_count += 1

        except Exception as e:
            try:
                print(f"! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"! ERROR: {str(e)}")
            results.append({
                'Page Name': page.name if 'page' in locals() else '[unknown]',
                'Wikidata QID': ''
            })
            not_found_count += 1

    # Write to CSV
    csv_filename = 'ancient_egyptian_decans_wikidata.csv'
    print(f"\n{'=' * 60}")
    print(f"\nWriting results to {csv_filename}...\n")

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Page Name', 'Wikidata QID']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in results:
                writer.writerow(row)

        print(f"✓ CSV file created: {csv_filename}")

        # Print summary
        print(f"\nSummary:")
        print(f"  Total members: {len(results)}")
        print(f"  Found QIDs: {found_count}")
        print(f"  Missing QIDs: {not_found_count}")

    except Exception as e:
        print(f"! Error writing CSV: {e}")


if __name__ == "__main__":
    main()
