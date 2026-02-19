"""
import_xml_batch.py
===================
Imports all XML files from the import/ directory into Shinto Wiki
using the MediaWiki import API.

Usage:
  python import_xml_batch.py
"""

import sys
import io
import os
import glob
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
THROTTLE     = 2.0  # seconds between imports

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
print("Logging in to Shinto Wiki...")
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH,
                     clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print("Logged in successfully.")

# ─── FIND ALL XML FILES ────────────────────────────────────────────
xml_files = sorted(glob.glob(os.path.join(IMPORT_DIR, 'shinto_wiki_import-*.xml')),
                   key=lambda f: int(os.path.basename(f).split('-')[1].split('.')[0]))

if not xml_files:
    print("No XML files found in import/ directory.")
    sys.exit(1)

print(f"Found {len(xml_files)} XML files to import.\n")

# ─── IMPORT EACH FILE ──────────────────────────────────────────────
success_count = 0
fail_count = 0
failed_files = []

for i, xml_path in enumerate(xml_files, 1):
    filename = os.path.basename(xml_path)
    print(f"[{i}/{len(xml_files)}] Importing {filename}...")

    with open(xml_path, 'rb') as f:
        xml_data = f.read()

    file_size_kb = len(xml_data) / 1024
    print(f"  File size: {file_size_kb:.1f} KB")

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

    try:
        res = site.connection.post(API_URL, data=data, files=files, timeout=300).json()
        if 'error' in res:
            err = res['error']
            print(f"  ERROR: {err.get('code')} - {err.get('info')}")
            fail_count += 1
            failed_files.append(filename)
        else:
            imported = res.get('import', [])
            page_count = len(imported)
            titles = [p.get('title', '?') for p in imported[:5]]
            preview = ', '.join(titles)
            if page_count > 5:
                preview += f', ... (+{page_count - 5} more)'
            print(f"  OK: {page_count} pages imported ({preview})")
            success_count += 1
    except APIError as e:
        print(f"  APIError: {e.code} - {e.info}")
        fail_count += 1
        failed_files.append(filename)
    except Exception as e:
        print(f"  Unexpected error: {e}")
        fail_count += 1
        failed_files.append(filename)

    if i < len(xml_files):
        time.sleep(THROTTLE)

# ─── SUMMARY ────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Import complete!")
print(f"  Success: {success_count}/{len(xml_files)} files")
print(f"  Failed:  {fail_count}/{len(xml_files)} files")
if failed_files:
    print(f"  Failed files: {', '.join(failed_files)}")
print(f"{'='*50}")
