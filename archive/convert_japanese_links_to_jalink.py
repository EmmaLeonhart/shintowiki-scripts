#!/usr/bin/env python3
"""
Convert Japanese wikilinks to {{jalink}} templates with Wikidata QIDs
Only processes links in the Japanese Wikipedia section
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

def get_qid_from_jawiki(page_title):
    """Get Wikidata QID from Japanese Wikipedia page title"""
    url = 'https://ja.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': page_title,
        'prop': 'pageprops',
        'format': 'json'
    }
    headers = {
        'User-Agent': 'ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id != '-1':  # Page exists
                pageprops = page_data.get('pageprops', {})
                wikibase_item = pageprops.get('wikibase_item')
                if wikibase_item:
                    return wikibase_item
    except:
        pass

    return None

def convert_japanese_links(text):
    """Convert Japanese wikilinks in Japanese section to {{jalink}} templates"""

    # Find the Japanese Wikipedia content section
    japanese_section_match = re.search(r'(== Japanese Wikipedia content ==.*)', text, re.DOTALL)
    if not japanese_section_match:
        return text, 0

    japanese_section_start = japanese_section_match.start()
    japanese_section = japanese_section_match.group(1)

    # Find all wikilinks in the Japanese section
    # Match [[text]] or [[text|display]]
    wikilink_pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'

    links_found = re.findall(wikilink_pattern, japanese_section)

    if not links_found:
        return text, 0

    # Process unique links
    unique_links = list(set(links_found))
    link_to_qid = {}

    print(f"  Found {len(unique_links)} unique Japanese links", flush=True)

    for link in unique_links:
        # Skip if it's a file, category, or has a colon (interwiki, etc)
        if ':' in link or link.startswith('Category:') or link.startswith('File:'):
            continue

        qid = get_qid_from_jawiki(link)
        link_to_qid[link] = qid

        if qid:
            print(f"    {link} → {qid}", flush=True)
        else:
            print(f"    {link} → (no QID)", flush=True)

        time.sleep(0.1)  # Small delay to avoid rate limiting

    # Now replace links in the Japanese section
    modified_section = japanese_section
    replacements_made = 0

    # Replace [[link|display]] first (with pipe)
    pipe_pattern = r'\[\[([^\]|]+)\|([^\]]+)\]\]'

    def replace_pipe_link(match):
        nonlocal replacements_made
        link = match.group(1)
        display = match.group(2)

        if ':' in link or link.startswith('Category:') or link.startswith('File:'):
            return match.group(0)  # Don't replace

        qid = link_to_qid.get(link)
        replacements_made += 1

        if qid:
            return f'{{{{jalink|{link}|{qid}|{display}}}}}'
        else:
            return f'{{{{jalink|{link}||{display}}}}}'

    modified_section = re.sub(pipe_pattern, replace_pipe_link, modified_section)

    # Replace [[link]] (without pipe)
    simple_pattern = r'\[\[([^\]|]+)\]\]'

    def replace_simple_link(match):
        nonlocal replacements_made
        link = match.group(1)

        if ':' in link or link.startswith('Category:') or link.startswith('File:'):
            return match.group(0)  # Don't replace

        qid = link_to_qid.get(link)
        replacements_made += 1

        if qid:
            return f'{{{{jalink|{link}|{qid}}}}}'
        else:
            return f'{{{{jalink|{link}}}}}'

    modified_section = re.sub(simple_pattern, replace_simple_link, modified_section)

    # Rebuild the page
    before_japanese = text[:japanese_section_start]
    new_text = before_japanese + modified_section

    return new_text, replacements_made

def main():
    print("=" * 80)
    print("CONVERT JAPANESE LINKS TO JALINK TEMPLATES")
    print("=" * 80)
    print()

    # Connect to wiki
    print("Connecting to wiki...", flush=True)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully", flush=True)
    print()

    # Get all pages in category
    category_name = 'Automerged Japanese text'
    print(f"Fetching pages from [[Category:{category_name}]]...", flush=True)
    category = site.categories[category_name]
    pages = list(category)
    print(f"Found {len(pages)} pages to process", flush=True)
    print()

    # Restart point - skip everything before this alphabetically
    START_FROM = "Ukanomitama"
    print(f">>> RESTARTING: Skipping all pages before [[{START_FROM}]] alphabetically <<<")
    print()

    processed = 0
    skipped = 0
    failed = 0
    total_replacements = 0
    skip_until_reached = False

    for i, page in enumerate(pages, 1):
        page_title = page.name

        # Skip pages before START_FROM alphabetically
        if not skip_until_reached:
            if page_title < START_FROM:
                print(f"[{i}/{len(pages)}] Skipping: [[{page_title}]] (before {START_FROM})", flush=True)
                skipped += 1
                continue
            else:
                skip_until_reached = True
                print(f">>> Reached starting point: [[{page_title}]] <<<", flush=True)

        print(f"[{i}/{len(pages)}] Processing: [[{page_title}]]", flush=True)

        if not page.exists:
            print(f"  ✗ Page doesn't exist, skipping", flush=True)
            skipped += 1
            continue

        try:
            # Get page text
            text = page.text()

            # Convert Japanese links
            new_text, replacements = convert_japanese_links(text)

            if replacements == 0:
                print(f"  No links to convert", flush=True)
                skipped += 1
                continue

            if new_text == text:
                print(f"  No changes made", flush=True)
                skipped += 1
                continue

            # Save the page
            page.save(new_text, summary=f'Convert {replacements} Japanese wikilinks to {{{{jalink}}}} templates with Wikidata QIDs')
            print(f"  ✓ Converted {replacements} links", flush=True)

            processed += 1
            total_replacements += replacements
            time.sleep(1.5)

        except Exception as e:
            print(f"  ✗ Failed: {e}", flush=True)
            failed += 1

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pages found: {len(pages)}")
    print(f"Pages processed: {processed}")
    print(f"Total link replacements: {total_replacements}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print()

if __name__ == '__main__':
    main()
