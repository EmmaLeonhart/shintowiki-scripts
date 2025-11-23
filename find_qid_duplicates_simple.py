#!/usr/bin/env python3
"""
find_qid_duplicates_simple.py
=============================
Simple direct approach to find QID duplicates using direct API calls with requests
"""

import requests
import re
import sys
import time
import csv
from collections import defaultdict

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'https://shinto.miraheze.org/w'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
CATEGORY  = 'Pages linked to Wikidata'

session = requests.Session()
session.headers.update({'User-Agent': 'Wikidata QID Finder Bot'})

print("Logging in...\n")

# Login
login_token_response = session.get(f'{WIKI_URL}/api.php', params={
    'action': 'query',
    'meta': 'tokens',
    'type': 'login',
    'format': 'json'
})

login_token = login_token_response.json()['query']['tokens']['logintoken']

login_response = session.post(f'{WIKI_URL}/api.php', data={
    'action': 'clientlogin',
    'username': USERNAME,
    'password': PASSWORD,
    'logintoken': login_token,
    'loginreturnurl': 'http://example.org/',
    'format': 'json'
})

if login_response.json()['clientlogin']['status'] != 'PASS':
    print(f"Login failed: {login_response.json()}")
    sys.exit(1)

print("Logged in\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_all_wikidata_qids(page_text):
    """Extract all Wikidata QIDs from page text."""
    matches = re.findall(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    qids = [match[0].upper() for match in matches]
    return qids

def get_category_members(category, limit=None):
    """Get all pages in a category."""
    pages = []
    continue_token = None

    while True:
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': 500,
            'format': 'json'
        }

        if continue_token:
            params['cmcontinue'] = continue_token

        response = session.get(f'{WIKI_URL}/api.php', params=params, timeout=30)
        data = response.json()

        if 'query' in data and 'categorymembers' in data['query']:
            for member in data['query']['categorymembers']:
                pages.append(member['title'])

                if limit and len(pages) >= limit:
                    return pages

        if 'continue' not in data:
            break

        continue_token = data['continue']['cmcontinue']

    return pages

def get_page_text(page_title):
    """Get the text of a page."""
    response = session.get(f'{WIKI_URL}/api.php', params={
        'action': 'query',
        'titles': page_title,
        'prop': 'extracts',
        'explaintext': True,
        'format': 'json'
    }, timeout=30)

    data = response.json()
    pages = data.get('query', {}).get('pages', {})

    for page_id, page_data in pages.items():
        return page_data.get('extract', '')

    return ''

# ─── MAIN LOGIC ──────────────────────────────────────────────

print(f"Fetching category members...\n")
pages = get_category_members(CATEGORY)
print(f"Found {len(pages)} pages\n")

# Process pages
qid_to_pages = defaultdict(list)
conflicting_pages = []

for i, page_title in enumerate(pages, 1):
    if i % 100 == 0:
        print(f"Processing {i}/{len(pages)}...")

    try:
        text = get_page_text(page_title)
        qids = extract_all_wikidata_qids(text)

        if len(qids) > 1:
            print(f"  ⚠ Conflict on {page_title}: {qids}")
            conflicting_pages.append(page_title)
        elif len(qids) == 1:
            qid_to_pages[qids[0]].append(page_title)

    except Exception as e:
        print(f"  ✗ Error on {page_title}: {e}")

    time.sleep(0.5)

print(f"\nProcessing complete!")
print(f"Found {len(conflicting_pages)} pages with conflicting QIDs\n")

# Write CSV file
print(f"Writing CSV file...")
with open('wikidata_qid_duplicates.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)

    # Find max number of pages for any QID
    max_pages = max(len(pages) for pages in qid_to_pages.values()) if qid_to_pages else 0

    # Write header
    writer.writerow(['Wikidata QID', 'Number of Pages'] + [f'Page {i+1}' for i in range(max_pages)])

    # Sort by number of pages (descending), then by QID
    sorted_qids = sorted(qid_to_pages.items(),
                        key=lambda x: (-len(x[1]), x[0]))

    for qid, page_list in sorted_qids:
        row = [qid, str(len(page_list))] + sorted(page_list)
        writer.writerow(row)

print(f"Wrote CSV with {len(qid_to_pages)} QIDs\n")

# Generate wiki markup for duplicates
duplicates = {qid: pages for qid, pages in qid_to_pages.items() if len(pages) >= 2}

print(f"Found {len(duplicates)} QIDs with duplicate links\n")

wiki_content = "== Wikidata QID Duplicates ==\n\n"
wiki_content += "This page lists all Wikidata QIDs that are linked from multiple pages in [[Category:Pages linked to Wikidata]].\n\n"
wiki_content += f"Total duplicate QIDs: {len(duplicates)}\n"
wiki_content += f"Total pages with conflicting QIDs: {len(conflicting_pages)}\n\n"

if conflicting_pages:
    wiki_content += "=== Pages with Conflicting QIDs ===\n\n"
    for page_name in sorted(conflicting_pages):
        wiki_content += f"* [[{page_name}]]\n"
    wiki_content += "\n"

# Sort by number of pages (descending)
sorted_duplicates = sorted(duplicates.items(),
                          key=lambda x: (-len(x[1]), x[0]))

wiki_content += "=== Duplicate QIDs ===\n\n"

for qid, page_list in sorted_duplicates:
    wiki_content += f"==== {qid} ({len(page_list)} pages) ====\n"
    wiki_content += f"{{{{wikidata link|{qid}}}}}\n\n"

    for page_name in sorted(page_list):
        wiki_content += f"* [[{page_name}]]\n"

    wiki_content += "\n"

# Write to file
with open('wikidata_qid_duplicates_report.wiki', 'w', encoding='utf-8') as f:
    f.write(wiki_content)

print(f"Wrote wiki report\n")

# Upload to wiki
print(f"Uploading report to [[User:Immanuelle/Wikidata duplicates]]...")

# Get edit token
csrf_response = session.get(f'{WIKI_URL}/api.php', params={
    'action': 'query',
    'meta': 'tokens',
    'type': 'csrf',
    'format': 'json'
})
csrf_token = csrf_response.json()['query']['tokens']['csrftoken']

# Edit page
edit_response = session.post(f'{WIKI_URL}/api.php', data={
    'action': 'edit',
    'title': 'User:Immanuelle/Wikidata duplicates',
    'text': wiki_content,
    'summary': 'Update wikidata duplicates report',
    'token': csrf_token,
    'format': 'json'
})

if 'edit' in edit_response.json() and edit_response.json()['edit']['result'] == 'Success':
    print(f"Successfully uploaded!\n")
else:
    print(f"Upload failed: {edit_response.json()}\n")

print(f"=== Summary ===")
print(f"Total pages processed: {len(pages)}")
print(f"Pages with single QID: {sum(len(p) for p in qid_to_pages.values())}")
print(f"Pages with conflicting QIDs: {len(conflicting_pages)}")
print(f"QIDs with duplicates: {len(duplicates)}")
print(f"QIDs total: {len(qid_to_pages)}")
