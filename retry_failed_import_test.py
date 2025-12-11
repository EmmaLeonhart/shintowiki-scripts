#!/usr/bin/env python3
"""
Test retry of failed import merge - testing on イギリス王室
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
TEST_PAGE = 'イギリス王室'

def get_qid_from_jawiki_title(ja_title):
    """Get Wikidata QID from Japanese Wikipedia title"""
    url = 'https://ja.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': ja_title,
        'prop': 'pageprops',
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
        pages = data['query']['pages']
        for page_id, page_data in pages.items():
            if 'pageprops' in page_data and 'wikibase_item' in page_data['pageprops']:
                return page_data['pageprops']['wikibase_item']
    except:
        pass

    return None

def get_redirect_target(site, page_title):
    """Get redirect target of a page"""
    page = site.pages[page_title]
    if not page.exists:
        return None

    # Check if it's a redirect
    if page.redirect:
        # Get redirect target
        text = page.text()
        match = re.search(r'#(?:REDIRECT|redirect)\s*\[\[([^\]]+)\]\]', text, re.IGNORECASE)
        if match:
            return match.group(1)

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

def main():
    print("=" * 80)
    print(f"TEST RETRY FAILED IMPORT: {TEST_PAGE}")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Step 1: Get Wikidata QID from Japanese title
    print("Step 1: Getting Wikidata QID from Japanese Wikipedia title...", flush=True)
    qid = get_qid_from_jawiki_title(TEST_PAGE)
    if not qid:
        print(f"  ERROR: Could not find QID for {TEST_PAGE}")
        return
    print(f"  Found QID: {qid}", flush=True)
    print()

    # Step 2: Check if QID page exists on wiki and get redirect target
    print("Step 2: Finding redirect target from QID page...", flush=True)
    english_title = get_redirect_target(site, qid)
    if not english_title:
        print(f"  ERROR: [[{qid}]] does not exist or is not a redirect")
        return
    print(f"  [[{qid}]] redirects to [[{english_title}]]", flush=True)
    print()

    # Step 3: Get Japanese content and revision ID
    print("Step 3: Getting Japanese Wikipedia content...", flush=True)
    ja_content = get_jawiki_content(TEST_PAGE)
    if not ja_content:
        print(f"  ERROR: Could not fetch content for {TEST_PAGE}")
        return
    print(f"  Fetched {len(ja_content)} characters", flush=True)

    ja_revid = get_jawiki_revid(TEST_PAGE)
    print(f"  Current revision ID: {ja_revid}", flush=True)
    print()

    # Step 4: Get English page current content
    print("Step 4: Getting English page content...", flush=True)
    en_page = site.pages[english_title]
    if not en_page.exists:
        print(f"  ERROR: English page [[{english_title}]] does not exist")
        return
    en_content = en_page.text()
    print(f"  Fetched {len(en_content)} characters from [[{english_title}]]", flush=True)
    print()

    # Step 5: Create merged content
    print("Step 5: Creating merged content...", flush=True)
    translation_template = f"\n\n{{{{translated page|ja|{TEST_PAGE}|version={ja_revid}|comment=Imported full ja history}}}}[[Category:Automerged Japanese text]]"
    japanese_section = f"\n\n== Japanese Wikipedia content ==\n{ja_content}\n\n==End Japanese=="
    merged_content = en_content + translation_template + japanese_section
    print(f"  Created merged content ({len(merged_content)} characters)", flush=True)
    print()

    # Step 6: Delete English page
    print("Step 6: Deleting English page...", flush=True)
    en_page.delete(reason="Preparing to merge Japanese Wikipedia import with full revision history")
    print(f"  ✓ Deleted [[{english_title}]]", flush=True)
    time.sleep(2)
    print()

    # Step 7: Move Japanese page to English page name
    print("Step 7: Moving Japanese page to English page name...", flush=True)
    ja_page = site.pages[TEST_PAGE]
    if not ja_page.exists:
        print(f"  ERROR: Japanese page [[{TEST_PAGE}]] does not exist!")
        return
    ja_page.move(english_title,
                reason="Merging Japanese Wikipedia import with English content",
                no_redirect=True)
    print(f"  ✓ Moved [[{TEST_PAGE}]] → [[{english_title}]]", flush=True)
    time.sleep(2)
    print()

    # Step 8: Undelete all revisions
    print("Step 8: Undeleting all revisions of English page...", flush=True)
    try:
        result = site.api('undelete',
                        title=english_title,
                        reason="Restoring English revisions to merge with Japanese Wikipedia history",
                        token=site.get_token('delete'))
        print(f"  ✓ Undeleted revisions", flush=True)
        time.sleep(2)
    except Exception as e:
        print(f"  Warning: {e}", flush=True)
    print()

    # Step 9: Overwrite with merged content
    print("Step 9: Overwriting with merged content...", flush=True)
    target_page = site.pages[english_title]
    target_page.save(merged_content,
                   summary="Merged Japanese Wikipedia content with full revision history and English content")
    print(f"  ✓ Saved merged content to [[{english_title}]]", flush=True)
    print()

    print("=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"Merged [[{TEST_PAGE}]] into [[{english_title}]]")
    print()

if __name__ == '__main__':
    main()
