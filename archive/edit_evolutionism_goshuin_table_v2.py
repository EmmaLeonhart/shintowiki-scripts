"""
Edit the Leonhart Shrine page on evolutionism.miraheze.org
- Add Wikidata links to Shrine name column
- Add P825 (dedicated to) column
"""

import mwclient
import requests
import sys
import time
import re
import json

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
PAGE_NAME = 'Leonhart Shrine'

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Image numbers from the wiki page
image_numbers = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
    40, 41, 42, 43, 44, 45, 46, 47,
    50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
    60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
    70, 71, 73, 74, 75, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94
]

# Categories to ignore
IGNORE_PATTERNS = [
    "Goshuincho", "CC-BY", "Creative Commons", "Self-published", "SDC",
    "license", "Files by", "Files from", "Uploaded via", "Media missing",
    "Images with", "PD-", "GFDL", "Duplicate", "Unidentified", "bad uploads",
    "Immanuelle's Goshuin"
]

def get_file_categories(filename):
    """Fetch categories for a file from Wikimedia Commons"""
    params = {
        'action': 'query',
        'titles': f'File:{filename}',
        'prop': 'categories',
        'cllimit': 'max',
        'format': 'json'
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers={'User-Agent': 'WikiBot/1.0'})
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id == '-1':
                return []
            categories = page_data.get('categories', [])
            cat_names = []
            for cat in categories:
                cat_title = cat.get('title', '')
                if cat_title.startswith('Category:'):
                    cat_name = cat_title[9:]
                    should_ignore = any(p.lower() in cat_name.lower() for p in IGNORE_PATTERNS)
                    if not should_ignore:
                        cat_names.append(cat_name)
            return cat_names
    except Exception as e:
        print(f"Error fetching {filename}: {e}")
        return []

def get_wikidata_from_commons_category(cat_name):
    """Get Wikidata QID from Commons category via P373 (Commons category)"""
    # Search for items that have this Commons category (P373)
    query = f'''
    SELECT ?item WHERE {{
      ?item wdt:P373 "{cat_name}" .
    }} LIMIT 1
    '''
    try:
        r = requests.get(WIKIDATA_SPARQL, params={'query': query, 'format': 'json'},
                        headers={'User-Agent': 'WikiBot/1.0'})
        data = r.json()
        bindings = data.get('results', {}).get('bindings', [])
        if bindings:
            uri = bindings[0]['item']['value']
            return uri.split('/')[-1]  # Extract QID from URI
    except Exception as e:
        print(f"  SPARQL error for {cat_name}: {e}")
    return None

def get_wikidata_info(qid):
    """Get English label and P825 (dedicated to) from Wikidata"""
    if not qid:
        return None, []

    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'props': 'labels|claims',
        'languages': 'en|ja',
        'format': 'json'
    }
    try:
        r = requests.get(WIKIDATA_API, params=params, headers={'User-Agent': 'WikiBot/1.0'})
        data = r.json()
        entity = data.get('entities', {}).get(qid, {})

        # Get English label (fallback to Japanese)
        labels = entity.get('labels', {})
        label = labels.get('en', {}).get('value') or labels.get('ja', {}).get('value') or qid

        # Get P825 (dedicated to) claims
        claims = entity.get('claims', {})
        p825_claims = claims.get('P825', [])
        dedicated_to = []
        for claim in p825_claims:
            mainsnak = claim.get('mainsnak', {})
            if mainsnak.get('snaktype') == 'value':
                datavalue = mainsnak.get('datavalue', {})
                if datavalue.get('type') == 'wikibase-entityid':
                    deity_qid = datavalue['value'].get('id')
                    if deity_qid:
                        dedicated_to.append(deity_qid)

        return label, dedicated_to
    except Exception as e:
        print(f"  Error fetching {qid}: {e}")
        return None, []

def get_labels_batch(qids):
    """Get English labels for multiple QIDs in one request"""
    if not qids:
        return {}

    labels = {}
    # Process in batches of 50
    for i in range(0, len(qids), 50):
        batch = qids[i:i+50]
        params = {
            'action': 'wbgetentities',
            'ids': '|'.join(batch),
            'props': 'labels',
            'languages': 'en|ja',
            'format': 'json'
        }
        try:
            r = requests.get(WIKIDATA_API, params=params, headers={'User-Agent': 'WikiBot/1.0'})
            data = r.json()
            entities = data.get('entities', {})
            for qid, entity in entities.items():
                entity_labels = entity.get('labels', {})
                label = entity_labels.get('en', {}).get('value') or entity_labels.get('ja', {}).get('value') or qid
                labels[qid] = label
        except Exception as e:
            print(f"  Batch label error: {e}")
        time.sleep(0.2)

    return labels

def main():
    # Connect to wiki
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='WikiBot/1.0 (https://evolutionism.miraheze.org/; immanuelle@example.com)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully!\n")

    # Step 1: Fetch Commons categories
    print("Step 1: Fetching categories from Wikimedia Commons...")
    commons_cats = {}
    for num in image_numbers:
        filename = f"Goshuincho of Emma Leonhart {num:02d}.jpg"
        categories = get_file_categories(filename)
        commons_cats[num] = categories[0] if categories else None
        if categories:
            print(f"  {num:02d}: {categories[0]}")
        else:
            print(f"  {num:02d}: (none)")
        time.sleep(0.2)

    # Step 2: Get Wikidata QIDs from Commons categories
    print("\nStep 2: Finding Wikidata items for each shrine...")
    shrine_data = {}  # num -> {qid, label, cat_name, dedicated_to_qids}
    all_deity_qids = set()

    for num, cat_name in commons_cats.items():
        if not cat_name:
            shrine_data[num] = {'qid': None, 'label': None, 'cat_name': None, 'dedicated_to': []}
            continue

        qid = get_wikidata_from_commons_category(cat_name)
        if qid:
            label, dedicated_to = get_wikidata_info(qid)
            shrine_data[num] = {
                'qid': qid,
                'label': label,
                'cat_name': cat_name,
                'dedicated_to': dedicated_to
            }
            all_deity_qids.update(dedicated_to)
            print(f"  {num:02d}: {qid} - {label} (P825: {dedicated_to})")
        else:
            shrine_data[num] = {'qid': None, 'label': None, 'cat_name': cat_name, 'dedicated_to': []}
            print(f"  {num:02d}: No Wikidata found for '{cat_name}'")
        time.sleep(0.3)

    # Step 3: Batch fetch deity labels
    print("\nStep 3: Fetching deity labels...")
    deity_labels = get_labels_batch(list(all_deity_qids))
    print(f"  Fetched {len(deity_labels)} deity labels")

    # Step 4: Build and save the table
    print(f"\nStep 4: Fetching and updating page: {PAGE_NAME}")
    page = site.pages[PAGE_NAME]
    old_text = page.text()

    # Build new table
    new_table_lines = [
        '{| class="wikitable sortable"',
        '! Image',
        '! Shrine name',
        '! Dedicated to',
        '! Commons category',
        '|-'
    ]

    for num in image_numbers:
        data = shrine_data[num]

        # Shrine name with Wikidata link
        if data['qid'] and data['label']:
            shrine_name = f"[[d:{data['qid']}|{data['label']}]]"
        else:
            shrine_name = ''

        # Dedicated to column
        if data['dedicated_to']:
            deity_links = []
            for deity_qid in data['dedicated_to']:
                deity_label = deity_labels.get(deity_qid, deity_qid)
                deity_links.append(f"[[d:{deity_qid}|{deity_label}]]")
            dedicated_to = '<br>'.join(deity_links)
        else:
            dedicated_to = ''

        # Commons category link
        if data['cat_name']:
            commons_cat = f"[[:commons:Category:{data['cat_name']}|{data['cat_name']}]]"
        else:
            commons_cat = ''

        new_table_lines.append(f'| [[File:Goshuincho of Emma Leonhart {num:02d}.jpg|50px]] || {shrine_name} || {dedicated_to} || {commons_cat}')
        new_table_lines.append('|-')

    new_table_lines.append('|}')
    new_table = '\n'.join(new_table_lines)

    # Find and replace the Goshuin table
    goshuin_header_pos = old_text.find('== Goshuin ==')
    if goshuin_header_pos == -1:
        print("ERROR: Could not find Goshuin section!")
        return

    table_start = old_text.find('{|', goshuin_header_pos)
    table_end = old_text.find('|}', table_start) + 2

    new_text = old_text[:table_start] + new_table + old_text[table_end:]

    print("\nSaving page...")
    page.save(new_text, summary="Add Wikidata links and P825 (dedicated to) column to Goshuin table")
    print("Done!")

if __name__ == '__main__':
    main()
