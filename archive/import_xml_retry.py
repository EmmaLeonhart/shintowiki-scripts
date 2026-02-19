"""
import_xml_retry.py
===================
Retries importing the failed XML files with retry logic and longer delays.
"""

import sys
import io
import os
import time
import mwclient
from mwclient.errors import APIError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL   = 'shinto.miraheze.org'
SHINTO_PATH  = '/w/'
API_URL      = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME     = 'Immanuelle'
PASSWORD     = '[REDACTED_SECRET_2]'
IMPORT_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'import')
MAX_RETRIES  = 3
THROTTLE     = 5.0  # longer delay between imports

FAILED_FILES = [
    'shinto_wiki_import-1.xml',
    'shinto_wiki_import-2.xml',
    'shinto_wiki_import-3.xml',
    'shinto_wiki_import-4.xml',
    'shinto_wiki_import-9.xml',
    'shinto_wiki_import-10.xml',
    'shinto_wiki_import-11.xml',
    'shinto_wiki_import-12.xml',
    'shinto_wiki_import-13.xml',
    'shinto_wiki_import-14.xml',
    'shinto_wiki_import-27.xml',
]


def login():
    print("Logging in to Shinto Wiki...")
    site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully.")
    return site


def import_file(site, xml_path, filename):
    with open(xml_path, 'rb') as f:
        xml_data = f.read()

    token = site.get_token('csrf')
    files = {'xml': (filename, xml_data, 'text/xml')}
    data = {
        'action': 'import',
        'format': 'json',
        'token': token,
        'interwikiprefix': 'ja',
        'assignknownusers': '1',
        'summary': 'Bot: batch import AI-translated shrine pages from jawiki'
    }

    res = site.connection.post(API_URL, data=data, files=files, timeout=300).json()
    if 'error' in res:
        err = res['error']
        raise Exception(f"API error: {err.get('code')} - {err.get('info')}")

    imported = res.get('import', [])
    page_count = len(imported)
    titles = [p.get('title', '?') for p in imported[:5]]
    preview = ', '.join(titles)
    if page_count > 5:
        preview += f', ... (+{page_count - 5} more)'
    return page_count, preview


site = login()

success_count = 0
still_failed = []

for i, filename in enumerate(FAILED_FILES, 1):
    xml_path = os.path.join(IMPORT_DIR, filename)
    file_size_kb = os.path.getsize(xml_path) / 1024
    print(f"\n[{i}/{len(FAILED_FILES)}] Retrying {filename} ({file_size_kb:.1f} KB)...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            page_count, preview = import_file(site, xml_path, filename)
            print(f"  OK (attempt {attempt}): {page_count} pages imported ({preview})")
            success_count += 1
            break
        except Exception as e:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                wait = THROTTLE * attempt * 2
                print(f"  Waiting {wait:.0f}s before retry...")
                time.sleep(wait)
                # Re-login in case session expired
                try:
                    site = login()
                except Exception as le:
                    print(f"  Re-login failed: {le}")
            else:
                still_failed.append(filename)

    time.sleep(THROTTLE)

print(f"\n{'='*50}")
print(f"Retry complete!")
print(f"  Success: {success_count}/{len(FAILED_FILES)} files")
print(f"  Still failed: {len(still_failed)}/{len(FAILED_FILES)} files")
if still_failed:
    print(f"  Still failed: {', '.join(still_failed)}")
print(f"{'='*50}")
