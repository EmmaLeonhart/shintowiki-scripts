#!/usr/bin/env python3
"""
Find pages in [[Category:Pages linked to Wikidata]] whose QIDs don't have P11250 (Miraheze article ID).
Outputs results to CSV with page title and QID for manual connection.
"""

import requests
import sys
import io
import csv
import mwclient
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def get_wikidata_entity(qid):
    """Fetch entity from Wikidata."""
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'format': 'json'
    }
    headers = {
        'User-Agent': 'Immanuelle/FindUnconnectedWikidata (https://shinto.miraheze.org; immanuelleproject@gmail.com)'
    }
    try:
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data['entities'].get(qid)
    except Exception as e:
        print(f"    Error fetching {qid}: {e}")
        return None

def has_miraheze_property(qid):
    """Check if Wikidata QID has P11250 (Miraheze article ID) property."""
    entity = get_wikidata_entity(qid)
    if not entity:
        return None  # Could not fetch

    claims = entity.get('claims', {})
    return 'P11250' in claims

def extract_qid_from_page(page_text):
    """Extract QID from {{wikidata link|QID}} template."""
    import re
    # Look for {{wikidata link|Qxxx}}
    match = re.search(r'\{\{wikidata link\|([Qq]\d+)\}\}', page_text)
    if match:
        qid = match.group(1).upper()
        return qid
    return None

def main():
    """Main execution."""
    print("="*70)
    print("FIND UNCONNECTED WIKIDATA QIDs")
    print("="*70)
    print()

    try:
        # Login to wiki
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        # Get all pages in category
        category_name = "Pages linked to Wikidata"
        print(f"Retrieving pages from [[Category:{category_name}]]...")

        unconnected_pages = []
        page_count = 0

        # Iterate through category members
        try:
            for page in site.api('query', list='categorymembers', cmtitle=f'Category:{category_name}', cmlimit='max')['query']['categorymembers']:
                page_title = page['title']
                page_ns = page['ns']

                # Only process mainspace pages (ns=0)
                if page_ns != 0:
                    continue

                page_count += 1
                print(f"Checking {page_count}: {page_title}...", end=" ")

                # Get page content
                try:
                    page_obj = site.pages[page_title]
                    page_text = page_obj.text()

                    # Extract QID from wikidata link template
                    qid = extract_qid_from_page(page_text)
                    if not qid:
                        print("[SKIP - no QID found]")
                        continue

                    # Check if P11250 exists
                    has_property = has_miraheze_property(qid)

                    if has_property is None:
                        print(f"[ERROR - could not fetch {qid}]")
                    elif not has_property:
                        print(f"[UNCONNECTED - {qid}]")
                        unconnected_pages.append({
                            'page_title': page_title,
                            'qid': qid
                        })
                    else:
                        print(f"[OK - {qid}]")

                except Exception as e:
                    print(f"[ERROR - {e}]")
                    continue

        except Exception as e:
            print(f"Error retrieving category members: {e}")
            import traceback
            traceback.print_exc()

        # Write results to CSV
        print(f"\n{'='*70}")
        print(f"Found {len(unconnected_pages)} unconnected pages")
        print(f"{'='*70}\n")

        if unconnected_pages:
            csv_filename = "unconnected_wikidata.csv"
            print(f"Writing results to {csv_filename}...")

            try:
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['page_title', 'qid']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(unconnected_pages)

                print(f"[OK] Wrote {len(unconnected_pages)} entries to {csv_filename}")
            except Exception as e:
                print(f"[ERROR] Failed to write CSV: {e}")
        else:
            print("No unconnected pages found!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
