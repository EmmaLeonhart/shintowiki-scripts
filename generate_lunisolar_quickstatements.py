"""generate_lunisolar_quickstatements.py
================================================
Generate QuickStatements for Lunisolar months and days

For days: Create P11250 and Den properties
For months: Create no description (Den property)
================================================
"""

import mwclient
import requests
import json
import re

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

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
    """Generate QuickStatements for lunisolar months and days."""

    print("Generating QuickStatements for Lunisolar months and days")
    print("=" * 60)

    # Get lunisolar days
    days_cat = site.pages['Category:Days of the Japanese Lunisolar Calendar']
    days = sorted(list(days_cat.members()), key=lambda p: p.name)

    print(f"\nFound {len(days)} lunisolar days")
    print(f"Generating QuickStatements...\n")

    quickstatements = []

    # Process each day
    for day_page in days:
        page_name = day_page.name
        text = day_page.text()
        qid = extract_wikidata_qid(text)

        if not qid:
            print(f"! {page_name} - No QID found")
            continue

        # Generate P11250 statement (shinto:Page Name)
        p11250_value = f"shinto:{page_name}"
        quickstatement = f'{qid}|P11250|"{p11250_value}"'
        quickstatements.append(quickstatement)

        # Generate Den statement (description)
        den_value = f"Day of the East Asian Lunisolar Calendar"
        quickstatement_den = f'{qid}|Den|"{den_value}"'
        quickstatements.append(quickstatement_den)

        print(f"[+] {page_name} ({qid})")

    # Get lunisolar months (P11250 only, no Den statements)
    months_cat = site.pages['Category:Lunisolar months']
    months = sorted(list(months_cat.members()), key=lambda p: p.name)

    print(f"\nFound {len(months)} lunisolar months")
    print(f"Generating P11250 statements for months...\n")

    # Process each month
    for month_page in months:
        page_name = month_page.name
        text = month_page.text()
        qid = extract_wikidata_qid(text)

        if not qid:
            print(f"! {page_name} - No QID found")
            continue

        # Generate P11250 statement (shinto:Page Name)
        p11250_value = f"shinto:{page_name}"
        quickstatement = f'{qid}|P11250|"{p11250_value}"'
        quickstatements.append(quickstatement)

        print(f"[+] {page_name} ({qid})")

    # Save to file
    output_file = 'lunisolar_quickstatements.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for statement in quickstatements:
            f.write(statement + '\n')

    print(f"\n{'=' * 60}")
    print(f"QuickStatements saved to: {output_file}")
    print(f"Total statements: {len(quickstatements)}")
    print(f"Days with P11250 and Den: {len(quickstatements) // 2}")

if __name__ == "__main__":
    main()
