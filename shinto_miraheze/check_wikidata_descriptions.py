#!/usr/bin/env python3
"""
check_wikidata_descriptions.py
==============================
Check pages in [[Category:Pages linked to Wikidata]] for English short descriptions
on their linked Wikidata items.

Adds:
- [[Category:Wikidata has short description]] if English short description exists
- [[Category:Wikidata no short description]] if no English short description exists
"""

import mwclient
import requests
import sys
import time
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
CATEGORY  = 'Pages linked to Wikidata'
HAS_DESC_CAT = 'Wikidata has short description'
NO_DESC_CAT = 'Wikidata no short description'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def get_wikidata_description(qid):
    """Get English short description from Wikidata."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if 'entities' in data and qid in data['entities']:
            descriptions = data['entities'][qid].get('descriptions', {})
            # Check if English description exists
            if 'en' in descriptions:
                return descriptions['en'].get('value')
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - wait longer
            print(f"    [RATE LIMITED] waiting...")
            time.sleep(5)
        return None
    except Exception as e:
        return None

def has_wikidata_description(qid):
    """Check if Wikidata item has English short description."""
    desc = get_wikidata_description(qid)
    if desc is None:
        return None  # Error fetching
    return bool(desc)

# ─── MAIN LOOP ───────────────────────────────────────────────

cat = site.pages[f'Category:{CATEGORY}']

if not cat.exists:
    print(f"[ERROR] Category '{CATEGORY}' does not exist")
    sys.exit(1)

print(f"[INFO] Processing pages in Category:{CATEGORY}\n")

count_has_desc = 0
count_no_desc = 0

for pg in cat:
    # Only process main namespace
    if pg.namespace != 0:
        continue

    try:
        print(f"Processing: {pg.name}")
        text = pg.text()

        # Extract QID
        qid = extract_wikidata_qid(text)
        if not qid:
            print(f"  [SKIP] no wikidata link found")
            continue

        print(f"  QID: {qid}")

        # Check if it has English short description
        has_desc = has_wikidata_description(qid)

        # If we can't fetch (None), treat as no description
        if has_desc is None:
            print(f"  [ERROR] could not fetch - assuming NO DESCRIPTION")
            has_desc = False

        if has_desc:
            print(f"  [HAS DESCRIPTION] adding category")
            target_cat = HAS_DESC_CAT
            count_has_desc += 1
        else:
            print(f"  [NO DESCRIPTION] adding category")
            target_cat = NO_DESC_CAT
            count_no_desc += 1

        # Add the appropriate category
        if f"[[Category:{target_cat}]]" not in text:
            new_text = text + f"\n[[Category:{target_cat}]]\n"
            try:
                pg.save(new_text, summary=f"Bot: Add {target_cat} - based on Wikidata English short description")
                print(f"  [DONE] category added")
            except Exception as e:
                print(f"  [FAILED] could not save: {e}")
        else:
            print(f"  [OK] category already present")

        time.sleep(1.5)

    except Exception as e:
        print(f"  [ERROR] {e}")

print(f"\nTotal pages with description: {count_has_desc}")
print(f"Total pages without description: {count_no_desc}")
