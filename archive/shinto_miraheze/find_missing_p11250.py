#!/usr/bin/env python3
"""
find_missing_p11250.py
======================
Find pages in [[Category:Pages linked to Wikidata]] whose linked Wikidata item
LACKS the Miraheze article ID (P11250) property entirely.

Adds [[Category:Wikidata missing P11250]] to these pages.
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
TARGET_CAT = 'Wikidata missing P11250'

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

def get_wikidata_properties(qid):
    """Get all properties of a Wikidata item."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if 'entities' in data and qid in data['entities']:
            return data['entities'][qid].get('claims', {})
        return {}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - wait longer
            print(f"    [RATE LIMITED] waiting...")
            time.sleep(5)
        # For other HTTP errors, skip this entry
        return None
    except Exception as e:
        return None

def has_p11250(qid):
    """Check if Wikidata item has P11250 property."""
    properties = get_wikidata_properties(qid)
    if properties is None:
        return None  # Error fetching
    return 'P11250' in properties

# ─── MAIN LOOP ───────────────────────────────────────────────

cat = site.pages[f'Category:{CATEGORY}']

if not cat.exists:
    print(f"[ERROR] Category '{CATEGORY}' does not exist")
    sys.exit(1)

print(f"[INFO] Processing pages in Category:{CATEGORY}\n")

count_no_p11250 = 0

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

        # Check if it has P11250
        has_prop = has_p11250(qid)
        if has_prop is None:
            print(f"  [ERROR] could not fetch from Wikidata")
            continue

        if has_prop:
            print(f"  [OK] has P11250")
        else:
            print(f"  [MISSING P11250] adding category")

            # Add the category
            if f"[[Category:{TARGET_CAT}]]" not in text:
                new_text = text + f"\n[[Category:{TARGET_CAT}]]\n"
                try:
                    pg.save(new_text, summary=f"Bot: Add {TARGET_CAT} - item lacks P11250 property")
                    count_no_p11250 += 1
                    print(f"  [DONE] category added")
                except Exception as e:
                    print(f"  [FAILED] could not save: {e}")
            else:
                print(f"  [OK] category already present")

        time.sleep(1.5)

    except Exception as e:
        print(f"  [ERROR] {e}")

print(f"\nTotal pages marked: {count_no_p11250}")
