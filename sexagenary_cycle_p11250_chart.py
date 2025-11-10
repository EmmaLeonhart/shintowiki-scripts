"""sexagenary_cycle_p11250_chart.py
================================================
Create chart of Sexagenary cycle members with P11250 property
================================================

This script:
1. Fetches all pages in [[Category:Sexagenary cycle members]]
2. Extracts the Wikidata QID from each page
3. Queries Wikidata for the P11250 property value
4. Outputs in format: QID | P11250 | value
"""

import mwclient
import requests
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
PASSWORD  = '[REDACTED_SECRET_1]'

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


def get_wikidata_p11250(qid):
    """Query Wikidata for P11250 property value."""
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        headers = {"User-Agent": "WikidataBot/1.0 (https://shinto.miraheze.org/; bot for checking wikidata links)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        entity = data.get('entities', {}).get(qid, {})

        # Look for P11250 property
        claims = entity.get('claims', {})
        p11250_claims = claims.get('P11250', [])

        if not p11250_claims:
            return None

        # Get the value of the first P11250 claim
        claim = p11250_claims[0]
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        value = datavalue.get('value', '')

        return value if value else None

    except Exception as e:
        print(f"     ! Error querying {qid}: {e}", file=sys.stderr)
        return None


def main():
    """Create P11250 chart for all Sexagenary cycle members."""

    print("Creating P11250 chart for Sexagenary cycle members\n")
    print("=" * 80)

    # Get the category
    category = site.pages['Category:Sexagenary cycle members']

    print(f"\nFetching all pages in [[Category:Sexagenary cycle members]]...")
    try:
        members = list(category.members())
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} members\n")

    # Data for chart and CSV
    chart_data = []
    csv_data = []

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end=" ... ")

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                print(f"✗ No QID found")
                continue

            print(f"({qid})", end=" ... ")

            # Query Wikidata for P11250
            p11250_value = get_wikidata_p11250(qid)

            if p11250_value:
                print(f"✓ P11250 found")
                chart_data.append({
                    'page_name': page_name,
                    'qid': qid,
                    'p11250': p11250_value
                })
                csv_data.append({
                    'Page Name': page_name,
                    'QID': qid,
                    'P11250': p11250_value
                })
            else:
                print(f"• No P11250 property")
                chart_data.append({
                    'page_name': page_name,
                    'qid': qid,
                    'p11250': ''
                })
                csv_data.append({
                    'Page Name': page_name,
                    'QID': qid,
                    'P11250': ''
                })

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")

    # Write chart to text file
    chart_filename = 'sexagenary_cycle_p11250_chart.txt'
    print(f"\n{'=' * 80}")
    print(f"\nWriting chart to {chart_filename}...\n")

    try:
        with open(chart_filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("SEXAGENARY CYCLE MEMBERS - P11250 PROPERTY CHART\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'QID':<12} | {'P11250 Value':<50}\n")
            f.write("-" * 80 + "\n")

            # Write chart data
            for item in chart_data:
                qid = item['qid']
                p11250 = item['p11250'] if item['p11250'] else '[none]'
                f.write(f"{qid:<12} | {p11250}\n")

        print(f"✓ Chart file created: {chart_filename}")

    except Exception as e:
        print(f"! Error writing chart file: {e}")

    # Write CSV
    csv_filename = 'sexagenary_cycle_p11250.csv'
    print(f"Writing CSV to {csv_filename}...\n")

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Page Name', 'QID', 'P11250']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in csv_data:
                writer.writerow(row)

        print(f"✓ CSV file created: {csv_filename}")

        # Summary
        with_p11250 = sum(1 for item in chart_data if item['p11250'])
        without_p11250 = sum(1 for item in chart_data if not item['p11250'])

        print(f"\nSummary:")
        print(f"  Total members: {len(chart_data)}")
        print(f"  With P11250: {with_p11250}")
        print(f"  Without P11250: {without_p11250}")

    except Exception as e:
        print(f"! Error writing CSV file: {e}")


if __name__ == "__main__":
    main()
