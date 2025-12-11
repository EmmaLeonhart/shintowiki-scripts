#!/usr/bin/env python3
"""
Import Japanese Wikipedia content with full revision history
Test on Ōarahiko Shrine first
"""

import sys
import io
import time
import mwclient
import requests
import re

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Test page
TEST_PAGE = 'Ōarahiko Shrine'

def get_wikidata_qid(site, page_name):
    """Get Wikidata QID from page"""
    page = site.pages[page_name]
    text = page.text()

    # Look for {{wikidata link|Q...}}
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

    print(f"  Response status: {response.status_code}", flush=True)
    print(f"  Response content length: {len(response.content)}", flush=True)

    if response.status_code != 200:
        print(f"  ERROR: HTTP {response.status_code}", flush=True)
        return None

    try:
        data = response.json()
    except Exception as e:
        print(f"  ERROR parsing JSON: {e}", flush=True)
        print(f"  Response text: {response.text[:500]}", flush=True)
        return None

    if 'entities' in data and qid in data['entities']:
        entity = data['entities'][qid]
        if 'sitelinks' in entity and 'jawiki' in entity['sitelinks']:
            return entity['sitelinks']['jawiki']['title']
    return None

def get_jawiki_content(ja_title):
    """Get Japanese Wikipedia article content"""
    site = mwclient.Site('ja.wikipedia.org',
                         clients_useragent='ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)')
    page = site.pages[ja_title]
    if page.exists:
        return page.text()
    return None

def get_jawiki_revid(ja_title):
    """Get current revision ID of Japanese Wikipedia article"""
    site = mwclient.Site('ja.wikipedia.org',
                         clients_useragent='ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)')
    page = site.pages[ja_title]
    if page.exists:
        return page.revision
    return None

def export_jawiki_xml(ja_title, output_file):
    """Export Japanese Wikipedia article with full history as XML"""
    print(f"  Exporting {ja_title} from Japanese Wikipedia...", flush=True)

    # Use API export
    url = 'https://ja.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': ja_title,
        'export': '1',
        'exportnowrap': '1',
        'format': 'xml'
    }
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }

    response = requests.get(url, params=params, headers=headers)

    with open(output_file, 'wb') as f:
        f.write(response.content)

    print(f"  Exported to {output_file}", flush=True)
    return len(response.content)

def main():
    """Main execution"""
    print("=" * 80)
    print("IMPORT JAPANESE WIKIPEDIA CONTENT WITH FULL HISTORY")
    print("=" * 80)
    print()
    print(f"Test page: {TEST_PAGE}")
    print()

    try:
        # Login to wiki
        print("Connecting to shinto.miraheze.org...", flush=True)
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)
        print("Logged in successfully", flush=True)
        print()

        # Step 1: Check if page has {{translated page|
        print("Step 1: Checking if page already has {{translated page|...", flush=True)
        page = site.pages[TEST_PAGE]
        if not page.exists:
            print(f"  ERROR: Page {TEST_PAGE} does not exist!")
            return

        current_text = page.text()
        if '{{translated page|' in current_text.lower():
            print(f"  Page already has {{{{translated page|}} template, skipping.")
            return

        print("  No {{translated page| found, proceeding...", flush=True)
        print()

        # Step 2: Get Japanese Wikipedia article name
        print("Step 2: Getting Japanese Wikipedia article name...", flush=True)
        qid = get_wikidata_qid(site, TEST_PAGE)
        if not qid:
            print(f"  ERROR: Could not find Wikidata QID for {TEST_PAGE}")
            return
        print(f"  Found QID: {qid}", flush=True)

        ja_title = get_jawiki_title_from_wikidata(qid)
        if not ja_title:
            print(f"  ERROR: Could not find Japanese Wikipedia article for {qid}")
            return
        print(f"  Found Japanese article: {ja_title}", flush=True)
        print()

        # Step 3: Get Japanese Wikipedia content
        print("Step 3: Fetching Japanese Wikipedia content...", flush=True)
        ja_content = get_jawiki_content(ja_title)
        if not ja_content:
            print(f"  ERROR: Could not fetch content for {ja_title}")
            return
        print(f"  Fetched {len(ja_content)} characters", flush=True)

        ja_revid = get_jawiki_revid(ja_title)
        print(f"  Current revision ID: {ja_revid}", flush=True)
        print()

        # Step 4: Create merged content
        print("Step 4: Creating merged content...", flush=True)

        # Find first English heading
        lines = current_text.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('==') and not line.strip().startswith('==='):
                insert_pos = i
                break

        # Insert Japanese section before first heading
        japanese_section = f"== Japanese Wikipedia content ==\n{ja_content}\n\n"

        merged_lines = lines[:insert_pos] + [japanese_section] + lines[insert_pos:]
        merged_content = '\n'.join(merged_lines)

        # Add template at bottom
        merged_content += f"\n\n{{{{translated page|ja|{ja_title}|version={ja_revid}|comment=Imported full ja history}}}}[[Category:Automerged Japanese text]]"

        print(f"  Created merged content ({len(merged_content)} characters)", flush=True)
        print()

        # Step 5: Export Japanese Wikipedia history
        print("Step 5: Exporting Japanese Wikipedia history...", flush=True)
        xml_file = f"{ja_title.replace('/', '_')}_export.xml"
        xml_size = export_jawiki_xml(ja_title, xml_file)
        print(f"  Exported {xml_size} bytes to {xml_file}", flush=True)
        print()

        # Step 6: Import XML
        print("Step 6: Importing XML to create Japanese page...", flush=True)
        print("  NOTE: This requires admin/import permissions and must be done via Special:Import")
        print(f"  You need to manually import {xml_file} via Special:Import")
        print(f"  URL: https://{WIKI_URL}/wiki/Special:Import")
        print()

        # Save merged content to file for later use
        merged_file = f"{TEST_PAGE.replace('/', '_')}_merged.txt"
        with open(merged_file, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        print(f"  Saved merged content to {merged_file}", flush=True)
        print()

        print("=" * 80)
        print("NEXT STEPS (after manual import):")
        print("=" * 80)
        print(f"1. Go to https://{WIKI_URL}/wiki/Special:Import")
        print(f"2. Upload {xml_file}")
        print(f"3. Import to create [[{ja_title}]]")
        print(f"4. Then run the merge script to:")
        print(f"   - Delete [[{TEST_PAGE}]]")
        print(f"   - Move [[{ja_title}]] to [[{TEST_PAGE}]]")
        print(f"   - Undelete all revisions of [[{TEST_PAGE}]]")
        print(f"   - Overwrite with content from {merged_file}")
        print()

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
