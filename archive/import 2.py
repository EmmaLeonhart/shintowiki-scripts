"""
everybodywiki_import_bot.py (v4)
================================
Imports full revision history of a page from EverybodyWiki into Shinto Wiki
by synthesizing an XML export and using the import API to preserve timestamps.

Configure PAGE_TITLE and credentials, then run:
  python everybodywiki_import_bot.py
"""

import sys
import time
import requests
import mwclient
from mwclient.errors import APIError
from xml.sax.saxutils import escape

# ─── CONFIG ─────────────────────────────────────────────────────────
EWWIKI_API   = 'https://en.everybodywiki.com/api.php'
SHINTO_URL   = 'shinto.miraheze.org'
SHINTO_PATH  = '/w/'
API_URL      = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME     = 'Immanuelle'
PASSWORD     = '[REDACTED_SECRET_1]'
PAGE_TITLE   = 'Superstitions_in_Christian_societies'
THROTTLE     = 1.0  # seconds between requests

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site.login(USERNAME, PASSWORD)

# ─── FETCH ALL REVISIONS VIA API ────────────────────────────────────
print(f"Fetching revisions for '{PAGE_TITLE}'...")
revisions = []
params = {
    'action': 'query',
    'format': 'json',
    'prop': 'revisions',
    'rvprop': 'ids|timestamp|content',
    'rvslots': 'main',
    'rvlimit': 'max',
    'rvdir': 'newer',
    'titles': PAGE_TITLE,
}
while True:
    resp = requests.get(EWWIKI_API, params=params)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get('query', {}).get('pages', {})
    pageinfo = next(iter(pages.values()), {})
    revs = pageinfo.get('revisions', [])
    if not revs:
        print(f"No revisions found for '{PAGE_TITLE}'. Exiting.")
        sys.exit(1)
    revisions.extend(revs)
    cont = data.get('continue', {}).get('rvcontinue')
    if not cont:
        break
    params['rvcontinue'] = cont
print(f"Total revisions fetched: {len(revisions)}")

# ─── BUILD XML EXPORT STRING ────────────────────────────────────────
print("Building XML for import...")
lines = ['<?xml version="1.0"?>', '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xml:lang="en">', f'<page>', f'  <title>{escape(PAGE_TITLE)}</title>']
for rev in revisions:
    ts   = rev['timestamp']
    rid  = rev['revid']
    text = rev.get('slots', {}).get('main', {}).get('*', rev.get('*', ''))
    lines.append('  <revision>')
    lines.append(f'    <timestamp>{escape(ts)}</timestamp>')
    lines.append(f'    <id>{rid}</id>')
    lines.append(f'    <text xml:space="preserve">{escape(text)}</text>')
    lines.append(f'    <contributor><username>Everybodywiki archive bot</username></contributor>')
    lines.append('  </revision>')
lines.append('</page>')
lines.append('</mediawiki>')
xml_data = '\n'.join(lines).encode('utf-8')
print(f"XML built ({len(xml_data)} bytes)")

# ─── IMPORT XML INTO SHINTO ─────────────────────────────────────────
print("Importing XML into Shinto...")
token = site.get_token('csrf')
files = {'xml': ('export.xml', xml_data, 'text/xml')}
data = {
    'action': 'import',
    'format': 'json',
    'token': token,
    'fullhistory': '1',
    'interwikiprefix': 'en'
}
try:
    res = site.connection.post(API_URL, data=data, files=files, timeout=300).json()
    if 'error' in res:
        err = res['error']
        print(f"Import error: {err.get('code')} - {err.get('info')}")
        sys.exit(1)
    print("Import complete; history with timestamps preserved.")
except APIError as e:
    print(f"APIError during import: {e.code} - {e.info}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)

print("Done.")
