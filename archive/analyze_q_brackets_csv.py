#!/usr/bin/env python3
"""
Analyze Q brackets pages and generate CSV with proposed English titles
"""

import sys
import io
import re
import csv
import mwclient
import requests

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def get_wikidata_qid(page):
    """Get Wikidata QID from page"""
    text = page.text()
    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def get_jawiki_title_from_wikidata(qid):
    """Get Japanese Wikipedia article title from Wikidata QID"""
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'props': 'sitelinks',
        'format': 'json'
    }
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }
    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        return None

    try:
        data = response.json()
        if 'entities' in data and qid in data['entities']:
            entity = data['entities'][qid]
            if 'sitelinks' in entity and 'jawiki' in entity['sitelinks']:
                return entity['sitelinks']['jawiki']['title']
    except:
        pass

    return None

def extract_japanese_brackets(ja_title):
    """Extract content from parentheses in Japanese title"""
    match = re.search(r'（([^）]+)）', ja_title)
    if match:
        return match.group(1)
    # Try regular ASCII parentheses too
    match = re.search(r'\(([^)]+)\)', ja_title)
    if match:
        return match.group(1)
    return None

def search_wikidata_by_japanese_label(japanese_text):
    """Search Wikidata for entity with Japanese label matching the text"""
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbsearchentities',
        'search': japanese_text,
        'language': 'ja',
        'limit': 5,
        'format': 'json'
    }
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if 'search' in data and len(data['search']) > 0:
            # Return the first match's QID
            return data['search'][0]['id']
    except:
        pass

    return None

def get_english_label_from_qid(qid):
    """Get English label from Wikidata QID"""
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'props': 'labels',
        'languages': 'en',
        'format': 'json'
    }
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if 'entities' in data and qid in data['entities']:
            entity = data['entities'][qid]
            if 'labels' in entity and 'en' in entity['labels']:
                return entity['labels']['en']['value']
    except:
        pass

    return None

def create_new_title(original_title, english_label):
    """Replace QID in brackets with English label"""
    # Extract the base name and QID from original title
    # e.g., "Hakusan Shrine (Q11579589)" -> "Hakusan Shrine" + "Q11579589"
    match = re.match(r'(.+?)\s*\((Q\d+)\)$', original_title)
    if match and english_label:
        base_name = match.group(1)
        return f"{base_name} ({english_label})"
    return None

def main():
    print("=" * 80)
    print("Q BRACKETS CSV ANALYSIS")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Get all pages in category
    category_name = 'Q brackets'
    print(f"Fetching pages from [[Category:{category_name}]]...", flush=True)
    category = site.categories[category_name]
    pages = list(category)
    print(f"Found {len(pages)} pages to analyze", flush=True)
    print()

    # Prepare CSV data
    csv_data = []

    for i, page in enumerate(pages, 1):
        original_title = page.name
        print(f"[{i}/{len(pages)}] Processing: {original_title}", flush=True)

        if not page.exists:
            print(f"  Page doesn't exist, skipping", flush=True)
            continue

        # Get QID from page
        qid = get_wikidata_qid(page)
        if not qid:
            print(f"  No Wikidata QID found, skipping", flush=True)
            continue

        print(f"  QID: {qid}", flush=True)

        # Get Japanese Wikipedia title
        ja_title = get_jawiki_title_from_wikidata(qid)
        if not ja_title:
            print(f"  No Japanese Wikipedia article found, skipping", flush=True)
            continue

        print(f"  Japanese title: {ja_title}", flush=True)

        # Extract Japanese bracket content
        ja_bracket_content = extract_japanese_brackets(ja_title)
        if not ja_bracket_content:
            print(f"  No brackets in Japanese title", flush=True)
            csv_data.append([original_title, ja_title, '', '', '', ''])
            continue

        print(f"  Japanese bracket content: {ja_bracket_content}", flush=True)

        # Search for QID of the bracket content
        bracket_qid = search_wikidata_by_japanese_label(ja_bracket_content)
        if not bracket_qid:
            print(f"  Could not find QID for bracket content", flush=True)
            csv_data.append([original_title, ja_title, ja_bracket_content, '', '', ''])
            continue

        print(f"  Bracket QID: {bracket_qid}", flush=True)

        # Get English label for bracket QID
        english_label = get_english_label_from_qid(bracket_qid)
        if not english_label:
            print(f"  No English label found for {bracket_qid}", flush=True)
            csv_data.append([original_title, ja_title, ja_bracket_content, bracket_qid, '', ''])
            continue

        print(f"  English label: {english_label}", flush=True)

        # Create new proposed title
        new_title = create_new_title(original_title, english_label)
        print(f"  Proposed new title: {new_title}", flush=True)

        csv_data.append([
            original_title,
            ja_title,
            ja_bracket_content,
            bracket_qid,
            english_label,
            new_title or ''
        ])
        print()

    # Write to CSV
    csv_filename = 'q_brackets_analysis.csv'
    print(f"Writing results to {csv_filename}...", flush=True)

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Original Title',
            'Japanese Title',
            'Japanese Bracket Content',
            'Bracket QID',
            'English Label',
            'Proposed New Title'
        ])
        writer.writerows(csv_data)

    print(f"CSV file created: {csv_filename}", flush=True)
    print(f"Total rows: {len(csv_data)}", flush=True)
    print()

if __name__ == '__main__':
    main()
