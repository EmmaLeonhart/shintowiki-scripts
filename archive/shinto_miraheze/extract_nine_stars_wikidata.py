"""extract_nine_stars_wikidata.py
================================================
Extract Wikidata QIDs for the Nine Stars and create a CSV
================================================

This script:
1. Queries for pages of each Nine Star
2. Extracts the Wikidata QID from each page
3. Creates a CSV with Star Name and QID
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

# The Nine Stars data
NINE_STARS = [
    "First White Water Star",
    "Second Black Earth Star",
    "Third Blue Wood Star",
    "Fourth Green Wood Star",
    "Fifth Yellow Earth Star",
    "Sixth White Metal Star",
    "Seventh Red Metal Star",
    "Eighth White Earth Star",
    "Ninth Purple Fire Star",
]

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


def get_page_wikidata(page_name):
    """Get the Wikidata QID for a page."""
    try:
        page = site.pages[page_name]
        if not page.exists:
            print(f"  ! Page does not exist: {page_name}")
            return None

        text = page.text()
        qid = extract_wikidata_qid(text)

        if qid:
            print(f"  ✓ Found {qid}")
            return qid
        else:
            print(f"  • No Wikidata QID found")
            return None

    except Exception as e:
        print(f"  ! Error: {e}")
        return None


def main():
    """Extract Wikidata for all Nine Stars."""

    print("Extracting Wikidata QIDs for Nine Stars\n")
    print("=" * 60)

    results = []

    for star_name in NINE_STARS:
        print(f"\n{star_name}")
        qid = get_page_wikidata(star_name)
        results.append({
            'Star Name': star_name,
            'Wikidata QID': qid if qid else ''
        })

    # Write to CSV
    csv_filename = 'nine_stars_wikidata.csv'
    print(f"\n{'=' * 60}")
    print(f"\nWriting results to {csv_filename}...\n")

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Star Name', 'Wikidata QID']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in results:
                writer.writerow(row)

        print(f"✓ CSV file created: {csv_filename}")

        # Print summary
        print(f"\nSummary:")
        found_count = sum(1 for r in results if r['Wikidata QID'])
        print(f"  Found QIDs for: {found_count}/{len(results)}")

    except Exception as e:
        print(f"! Error writing CSV: {e}")


if __name__ == "__main__":
    main()
