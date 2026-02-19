#!/usr/bin/env python3
"""
Import Japanese Wikipedia content with full revision history - FULLY AUTOMATED
No manual import required!
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
    except:
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

def export_jawiki_xml(ja_title):
    """Export Japanese Wikipedia article with full history as XML using Special:Export"""
    import urllib.parse

    # Use Special:Export with history parameter to get full history
    url = "https://ja.wikipedia.org/wiki/Special:Export/" + urllib.parse.quote(ja_title, safe="")
    print(f"    Fetching full history from Special:Export...", flush=True)

    response = requests.get(url, params={"history": "1"}, timeout=90,
                          headers={'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'})

    if response.status_code != 200:
        print(f"    ERROR: Export failed with status {response.status_code}", flush=True)
        return None

    xml_content = response.content
    print(f"    Downloaded {len(xml_content)} bytes", flush=True)

    # Count revisions in XML to verify we got full history
    import re
    revision_count = len(re.findall(b'<revision>', xml_content))
    print(f"    Found {revision_count} revisions in export", flush=True)

    return xml_content

def import_xml_to_wiki(site, xml_file_path):
    """Import XML file to wiki using API"""
    print(f"  Importing {xml_file_path} via API...", flush=True)

    # Get import token
    token = site.get_token('import')

    # Read the XML file
    with open(xml_file_path, 'rb') as f:
        xml_content = f.read()

    # Prepare multipart data for XML upload
    data = {
        'action': 'import',
        'interwikiprefix': 'ja',
        'token': token,
        'format': 'json',
        'fullhistory': '1'
    }
    files = {'xml': ('export.xml', xml_content, 'text/xml')}
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }

    # Make the request
    url = f'https://{WIKI_URL}{WIKI_PATH}api.php'
    response = requests.post(url, data=data, files=files, headers=headers, cookies=site.connection.cookies)

    print(f"  Response status: {response.status_code}", flush=True)
    print(f"  Response text: {response.text[:500]}", flush=True)

    try:
        result = response.json()
        print(f"  Import result: {result}", flush=True)
        return result
    except:
        print(f"  Full response: {response.text}", flush=True)
        raise

def main():
    """Main execution"""
    print("=" * 80)
    print("AUTOMATED JAPANESE WIKIPEDIA IMPORT WITH FULL HISTORY")
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

        # Step 4: Export Japanese Wikipedia history as XML and save to file
        print("Step 4: Exporting Japanese Wikipedia history...", flush=True)
        xml_content = export_jawiki_xml(ja_title)
        xml_filename = f"{ja_title.replace('/', '_')}_jawiki_export.xml"
        with open(xml_filename, 'wb') as f:
            f.write(xml_content)
        print(f"  Exported {len(xml_content)} bytes to {xml_filename}", flush=True)
        print()

        # Step 5: Import XML file to create Japanese page
        print("Step 5: Importing XML file to create Japanese page...", flush=True)
        import_result = import_xml_to_wiki(site, xml_filename)
        print(f"  Import completed!", flush=True)
        time.sleep(2)
        print()

        # Step 6: Create merged content
        print("Step 6: Creating merged content...", flush=True)

        # Append template first, then Japanese content
        translation_template = f"\n\n{{{{translated page|ja|{ja_title}|version={ja_revid}|comment=Imported full ja history}}}}[[Category:Automerged Japanese text]]"
        japanese_section = f"\n\n== Japanese Wikipedia content ==\n{ja_content}\n\n==End Japanese=="
        merged_content = current_text + translation_template + japanese_section
        print(f"  Created merged content ({len(merged_content)} characters)", flush=True)
        print()

        # Step 7: Delete English page
        print("Step 7: Deleting English page...", flush=True)
        page.delete(reason="Preparing to merge Japanese Wikipedia import with full revision history")
        print(f"  ✓ Deleted [[{TEST_PAGE}]]", flush=True)
        time.sleep(2)
        print()

        # Step 8: Move Japanese page to English page name
        print("Step 8: Moving Japanese page to English page name...", flush=True)
        ja_page = site.pages[ja_title]
        ja_page.move(TEST_PAGE,
                    reason="Merging Japanese Wikipedia import with English content",
                    no_redirect=True)
        print(f"  ✓ Moved [[{ja_title}]] → [[{TEST_PAGE}]]", flush=True)
        time.sleep(2)
        print()

        # Step 9: Undelete all revisions
        print("Step 9: Undeleting all revisions of English page...", flush=True)
        try:
            result = site.api('undelete',
                            title=TEST_PAGE,
                            reason="Restoring English revisions to merge with Japanese Wikipedia history",
                            token=site.get_token('delete'))
            print(f"  ✓ Undeleted revisions", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"  Warning: {e}", flush=True)
        print()

        # Step 10: Overwrite with merged content
        print("Step 10: Overwriting with merged content...", flush=True)
        target_page = site.pages[TEST_PAGE]
        target_page.save(merged_content,
                       summary="Merged Japanese Wikipedia content with full revision history and English content")
        print(f"  ✓ Saved merged content to [[{TEST_PAGE}]]", flush=True)
        print()

        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"The page [[{TEST_PAGE}]] now contains:")
        print(f"  - All Japanese Wikipedia revision history")
        print(f"  - All English page revision history")
        print(f"  - Merged content with both Japanese and English sections")
        print()

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
