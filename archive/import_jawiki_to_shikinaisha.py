#!/usr/bin/env python3
"""
import_jawiki_to_shikinaisha.py
================================
For all pages in Category:Wikidata generated shikinaisha pages:
1. Get Japanese Wikipedia content via Wikidata sitelink
2. Add it under == Japanese content == section
3. Demote all == headers to === (subsections)
4. Move categories to == Categories == section
5. Convert Japanese wikilinks to {{jalink|}} templates
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

SLEEP = 1.5

# No skip logic - let the "Already has Japanese content" check handle it
START_AFTER = None

# Cache for QID lookups
_qid_cache = {}

def get_wikidata_qid(text):
    """Extract Wikidata QID from page text"""
    match = re.search(r'\{\{wikidata link\|([Qq]\d+)\}\}', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
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
    headers = {'User-Agent': 'ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)'}

    try:
        time.sleep(0.3)  # Rate limit
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()

        if 'entities' in data and qid in data['entities']:
            entity = data['entities'][qid]
            if 'sitelinks' in entity and 'jawiki' in entity['sitelinks']:
                return entity['sitelinks']['jawiki']['title']
    except Exception as e:
        print(f"    Error fetching Wikidata: {e}", flush=True)

    return None

def get_jawiki_content(ja_title):
    """Get Japanese Wikipedia article content"""
    try:
        ja_site = mwclient.Site('ja.wikipedia.org',
                               clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
        page = ja_site.pages[ja_title]
        if page.exists:
            return page.text()
    except Exception as e:
        print(f"    Error fetching jawiki content: {e}", flush=True)
    return None

def get_qid_from_jawiki(page_title):
    """Get Wikidata QID from Japanese Wikipedia page title"""
    if page_title in _qid_cache:
        return _qid_cache[page_title]

    url = 'https://ja.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': page_title,
        'prop': 'pageprops',
        'format': 'json'
    }
    headers = {'User-Agent': 'ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)'}

    try:
        time.sleep(0.1)
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id != '-1':
                pageprops = page_data.get('pageprops', {})
                wikibase_item = pageprops.get('wikibase_item')
                if wikibase_item:
                    _qid_cache[page_title] = wikibase_item
                    return wikibase_item
    except:
        pass

    _qid_cache[page_title] = None
    return None

def extract_categories(text):
    """Extract all [[Category:...]] from text, return (text_without_cats, list_of_cats)"""
    cat_pattern = r'\[\[Category:[^\]]+\]\]'
    categories = re.findall(cat_pattern, text, re.IGNORECASE)
    text_without_cats = re.sub(cat_pattern, '', text, flags=re.IGNORECASE)
    return text_without_cats.strip(), categories

def demote_headers(text):
    """Convert == headers to === (demote by one level)"""
    # Match == Header == but not === Header ===
    # We need to be careful to only demote top-level headers
    lines = text.split('\n')
    result = []
    for line in lines:
        # Check if it's a level 2 header (== text ==)
        if re.match(r'^==([^=].*[^=])==\s*$', line):
            # Demote to level 3
            line = '=' + line + '='
        result.append(line)
    return '\n'.join(result)

def convert_japanese_links(text):
    """Convert Japanese wikilinks to {{jalink}} templates"""
    # Find all wikilinks
    replacements = 0

    # Handle [[link|display]] format
    def replace_pipe_link(match):
        nonlocal replacements
        link = match.group(1)
        display = match.group(2)

        # Skip categories, files, interwikis
        if ':' in link:
            return match.group(0)

        qid = get_qid_from_jawiki(link)
        replacements += 1

        if qid:
            return f'{{{{jalink|{link}|{qid}|{display}}}}}'
        else:
            return f'{{{{jalink|{link}||{display}}}}}'

    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', replace_pipe_link, text)

    # Handle [[link]] format
    def replace_simple_link(match):
        nonlocal replacements
        link = match.group(1)

        # Skip categories, files, interwikis
        if ':' in link:
            return match.group(0)

        qid = get_qid_from_jawiki(link)
        replacements += 1

        if qid:
            return f'{{{{jalink|{link}|{qid}}}}}'
        else:
            return f'{{{{jalink|{link}}}}}'

    text = re.sub(r'\[\[([^\]|]+)\]\]', replace_simple_link, text)

    return text, replacements

def process_page(page, site):
    """Process a single page"""
    page_title = page.name
    text = page.text()

    # Check if already has Japanese content section
    if '== Japanese content ==' in text or '==Japanese content==' in text:
        return None, "Already has Japanese content"

    # Get Wikidata QID
    qid = get_wikidata_qid(text)
    if not qid:
        return None, "No Wikidata QID found"

    # Get Japanese Wikipedia title
    ja_title = get_jawiki_title_from_wikidata(qid)
    if not ja_title:
        return None, "No jawiki sitelink"

    print(f"    Found jawiki: {ja_title}", flush=True)

    # Get Japanese content
    ja_content = get_jawiki_content(ja_title)
    if not ja_content:
        return None, "Could not fetch jawiki content"

    print(f"    Fetched {len(ja_content)} chars", flush=True)

    # Extract categories from Japanese content
    ja_content_no_cats, ja_categories = extract_categories(ja_content)

    # Demote headers in Japanese content
    ja_content_demoted = demote_headers(ja_content_no_cats)

    # Convert Japanese links to jalink templates
    ja_content_converted, link_count = convert_japanese_links(ja_content_demoted)
    print(f"    Converted {link_count} links to jalink", flush=True)

    # Extract existing categories from page
    text_no_cats, existing_cats = extract_categories(text)

    # Build new page content
    # Remove any existing == Categories == section
    text_no_cats = re.sub(r'== ?Categories ?==.*?(?=\n==|\Z)', '', text_no_cats, flags=re.DOTALL)
    text_no_cats = text_no_cats.strip()

    # Combine categories (existing + jawiki)
    all_categories = existing_cats + ja_categories
    # Remove duplicates while preserving order
    seen = set()
    unique_cats = []
    for cat in all_categories:
        cat_lower = cat.lower()
        if cat_lower not in seen:
            seen.add(cat_lower)
            unique_cats.append(cat)

    # Build final content
    new_content = text_no_cats
    new_content += f"\n\n== Japanese content ==\n{ja_content_converted}\n"

    if unique_cats:
        new_content += "\n== Categories ==\n"
        new_content += '\n'.join(unique_cats)
        new_content += '\n'

    return new_content, f"Added Japanese content, {link_count} links converted"

def main():
    print("=" * 80)
    print("IMPORT JAWIKI TO SHIKINAISHA PAGES")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Get pages from category
    category_name = 'Wikidata generated shikinaisha pages'
    print(f"Fetching pages from [[Category:{category_name}]]...", flush=True)
    category = site.categories[category_name]
    pages = list(category)
    print(f"Found {len(pages)} pages to process", flush=True)
    print()

    processed = 0
    skipped = 0
    failed = 0

    started = (START_AFTER is None)

    for i, page in enumerate(pages, 1):
        page_title = page.name

        if not started:
            if page_title == START_AFTER:
                started = True
                print(f"[RESUME] Starting after {START_AFTER}", flush=True)
            continue

        print(f"[{i}/{len(pages)}] {page_title}", flush=True)

        if page.namespace != 0:
            print(f"    Skipping (not mainspace)", flush=True)
            skipped += 1
            continue

        try:
            new_content, status = process_page(page, site)

            if new_content is None:
                print(f"    Skipped: {status}", flush=True)
                skipped += 1
            else:
                page.save(new_content, summary=f'Import Japanese Wikipedia content: {status}')
                print(f"    ✓ {status}", flush=True)
                processed += 1

        except Exception as e:
            print(f"    ✗ Failed: {e}", flush=True)
            failed += 1

        time.sleep(SLEEP)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pages: {len(pages)}")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")

if __name__ == '__main__':
    main()
