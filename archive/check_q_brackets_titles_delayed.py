#!/usr/bin/env python3
"""
Wait 30 minutes, then check pages in Category:Q brackets
Compare jawiki titles with internal titles
"""

import sys
import io
import time
import re
import mwclient
import requests

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Wait time in seconds (30 minutes = 1800 seconds)
WAIT_TIME = 1800

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

def main():
    print("=" * 80)
    print("DELAYED Q BRACKETS TITLE CHECK")
    print("=" * 80)
    print()
    print(f"Waiting 30 minutes ({WAIT_TIME} seconds) before processing...")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Wait 30 minutes
    time.sleep(WAIT_TIME)

    print()
    print("=" * 80)
    print("WAIT COMPLETE - STARTING TITLE COMPARISON")
    print("=" * 80)
    print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
    print(f"Found {len(pages)} pages to check", flush=True)
    print()

    matches = []
    mismatches = []
    no_qid = []
    no_jawiki = []

    for i, page in enumerate(pages, 1):
        page_title = page.name
        print(f"[{i}/{len(pages)}] Checking: {page_title}", flush=True)

        if not page.exists:
            print(f"  Page doesn't exist, skipping", flush=True)
            continue

        # Get QID
        qid = get_wikidata_qid(page)
        if not qid:
            print(f"  No Wikidata QID found", flush=True)
            no_qid.append(page_title)
            continue

        print(f"  QID: {qid}", flush=True)

        # Get Japanese Wikipedia title
        ja_title = get_jawiki_title_from_wikidata(qid)
        if not ja_title:
            print(f"  No Japanese Wikipedia article found", flush=True)
            no_jawiki.append((page_title, qid))
            continue

        print(f"  Japanese title: {ja_title}", flush=True)

        # Compare titles
        if page_title == ja_title:
            print(f"  ✓ MATCH: [[{page_title}]] = jawiki:{ja_title}", flush=True)
            matches.append((page_title, ja_title))
        else:
            print(f"  ✗ MISMATCH: [[{page_title}]] ≠ jawiki:{ja_title}", flush=True)
            mismatches.append((page_title, ja_title))

        print()

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print(f"Total pages checked: {len(pages)}")
    print(f"Matches: {len(matches)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"No QID: {len(no_qid)}")
    print(f"No jawiki: {len(no_jawiki)}")
    print()

    if mismatches:
        print("=" * 80)
        print("MISMATCHES:")
        print("=" * 80)
        for internal, jawiki in mismatches:
            print(f"  [[{internal}]] ≠ jawiki:{jawiki}")
        print()

    if no_qid:
        print("=" * 80)
        print("NO QID FOUND:")
        print("=" * 80)
        for title in no_qid:
            print(f"  [[{title}]]")
        print()

    if no_jawiki:
        print("=" * 80)
        print("NO JAWIKI ARTICLE:")
        print("=" * 80)
        for title, qid in no_jawiki:
            print(f"  [[{title}]] ({qid})")
        print()

    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

if __name__ == '__main__':
    main()
