#!/usr/bin/env python3
"""
check_wikidata_labels.py
==============================
Check pages in [[Category:Pages linked to Wikidata]] for English language labels
on their linked Wikidata items.

Adds:
- [[Category:Wikidata has English label]] if English label exists
- [[Category:Wikidata no English label]] if no English label exists
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
PASSWORD  = '[REDACTED_SECRET_1]'
CATEGORY  = 'Pages linked to Wikidata'
HAS_LABEL_CAT = 'Wikidata has English label'
NO_LABEL_CAT = 'Wikidata no English label'

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

def get_wikidata_label(qid):
    """Get English label from Wikidata."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if 'entities' in data and qid in data['entities']:
            labels = data['entities'][qid].get('labels', {})
            # Check if English label exists
            if 'en' in labels:
                return labels['en'].get('value')
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - wait longer
            print(f"    [RATE LIMITED] waiting...")
            time.sleep(5)
        return None
    except Exception as e:
        return None

def has_wikidata_label(qid):
    """Check if Wikidata item has English label."""
    label = get_wikidata_label(qid)
    if label is None:
        return None  # Error fetching
    return bool(label)

# ─── MAIN LOOP ───────────────────────────────────────────────

cat = site.pages[f'Category:{CATEGORY}']

if not cat.exists:
    print(f"[ERROR] Category '{CATEGORY}' does not exist")
    sys.exit(1)

print(f"[INFO] Processing pages in Category:{CATEGORY} for English labels\n")

count_has_label = 0
count_no_label = 0

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

        # Check if it has English label
        has_label = has_wikidata_label(qid)

        # If we can't fetch (None), treat as no label
        if has_label is None:
            print(f"  [ERROR] could not fetch - assuming NO LABEL")
            has_label = False

        if has_label:
            print(f"  [HAS LABEL] adding category")
            target_cat = HAS_LABEL_CAT
            count_has_label += 1
        else:
            print(f"  [NO LABEL] adding category")
            target_cat = NO_LABEL_CAT
            count_no_label += 1

        # Add the appropriate category
        if f"[[Category:{target_cat}]]" not in text:
            new_text = text + f"\n[[Category:{target_cat}]]\n"
            try:
                pg.save(new_text, summary=f"Bot: Add {target_cat} - based on Wikidata English label")
                print(f"  [DONE] category added")
            except Exception as e:
                print(f"  [FAILED] could not save: {e}")
        else:
            print(f"  [OK] category already present")

        time.sleep(1.5)

    except Exception as e:
        print(f"  [ERROR] {e}")

print(f"\nTotal pages with English label: {count_has_label}")
print(f"Total pages without English label: {count_no_label}")
