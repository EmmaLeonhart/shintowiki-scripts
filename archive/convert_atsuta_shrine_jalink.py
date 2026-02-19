#!/usr/bin/env python3
"""
Convert Japanese links to jalink templates on Atsuta Shrine only
"""

import sys
import io
import re
import mwclient
import requests
import time

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

# Connect to wiki
print("Connecting to wiki...", flush=True)
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print("Logged in successfully", flush=True)

# Get page
page = site.pages['Atsuta Shrine']
text = page.text()

# Find Japanese section
japanese_section_match = re.search(r'(== Japanese Wikipedia content ==.*)', text, re.DOTALL)
if not japanese_section_match:
    print('No Japanese section found')
    sys.exit(0)

japanese_section_start = japanese_section_match.start()
japanese_section = japanese_section_match.group(1)

# Find all wikilinks
wikilink_pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
links_found = re.findall(wikilink_pattern, japanese_section)

if not links_found:
    print('No links found')
    sys.exit(0)

unique_links = list(set(links_found))
link_to_qid = {}

print(f'Found {len(unique_links)} unique Japanese links', flush=True)

for link in unique_links:
    if ':' in link or link.startswith('Category:') or link.startswith('File:'):
        continue
    qid = get_qid_from_jawiki(link)
    link_to_qid[link] = qid
    if qid:
        print(f'  {link} → {qid}', flush=True)
    else:
        print(f'  {link} → (no QID)', flush=True)
    time.sleep(0.1)

# Replace links
modified_section = japanese_section
replacements_made = 0

# Replace [[link|display]] first
pipe_pattern = r'\[\[([^\]|]+)\|([^\]]+)\]\]'

def replace_pipe_link(match):
    global replacements_made
    link = match.group(1)
    display = match.group(2)
    if ':' in link or link.startswith('Category:') or link.startswith('File:'):
        return match.group(0)
    qid = link_to_qid.get(link)
    replacements_made += 1
    if qid:
        return f'{{{{jalink|{link}|{qid}|{display}}}}}'
    else:
        return f'{{{{jalink|{link}||{display}}}}}'

modified_section = re.sub(pipe_pattern, replace_pipe_link, modified_section)

# Replace [[link]]
simple_pattern = r'\[\[([^\]|]+)\]\]'

def replace_simple_link(match):
    global replacements_made
    link = match.group(1)
    if ':' in link or link.startswith('Category:') or link.startswith('File:'):
        return match.group(0)
    qid = link_to_qid.get(link)
    replacements_made += 1
    if qid:
        return f'{{{{jalink|{link}|{qid}}}}}'
    else:
        return f'{{{{jalink|{link}}}}}'

modified_section = re.sub(simple_pattern, replace_simple_link, modified_section)

# Rebuild page
before_japanese = text[:japanese_section_start]
new_text = before_japanese + modified_section

if new_text != text:
    page.save(new_text, summary=f'Convert {replacements_made} Japanese wikilinks to {{{{jalink}}}} templates with Wikidata QIDs')
    print(f'✓ Converted {replacements_made} links on [[Atsuta Shrine]]', flush=True)
else:
    print('No changes made', flush=True)
