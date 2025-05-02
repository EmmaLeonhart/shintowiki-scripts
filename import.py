"""
everybodywiki_import_bot.py (v6)
================================
Imports full revision history of a page from EverybodyWiki into Shinto Wiki, plus snapshot metadata from the Edithistory page.

Configure PAGE_TITLE and credentials, then run:
  python everybodywiki_import_bot.py
"""

import sys
import time
import re
import requests
import mwclient
from xml.sax.saxutils import escape

# ─── CONFIG ─────────────────────────────────────────────────────────
EWWIKI_API    = 'https://en.everybodywiki.com/api.php'
SHINTO_URL    = 'shinto.miraheze.org'
SHINTO_PATH   = '/w/'
API_URL       = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME      = 'Immanuelle'
PASSWORD      = '[REDACTED_SECRET_1]'
PAGE_TITLE    = 'TTT_(programme)'
THROTTLE      = 1.0  # seconds between HTTP/API calls
SNAPSHOT_PAGE = 'Edithistory:' + PAGE_TITLE
SNAPSHOT_URL  = f'https://en.everybodywiki.com/{SNAPSHOT_PAGE}'

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in to {SHINTO_URL} as {site.userinfo.get('name')}")

# ─── FETCH ALL REVISIONS VIA API ────────────────────────────────────
print(f"Fetching actual revisions for '{PAGE_TITLE}' from EverybodyWiki...")
revisions = []
params = {
    'action': 'query', 'format': 'json', 'prop': 'revisions',
    'rvprop': 'ids|timestamp|user|comment|content', 'rvslots': 'main',
    'rvlimit': 'max', 'rvdir': 'newer', 'titles': PAGE_TITLE
}
while True:
    resp = requests.get(EWWIKI_API, params=params)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get('query', {}).get('pages', {})
    pageinfo = next(iter(pages.values()), {})
    revs = pageinfo.get('revisions', [])
    if not revs:
        print(f"No actual revisions found for '{PAGE_TITLE}'. Exiting.")
        sys.exit(1)
    revisions.extend(revs)
    cont = data.get('continue', {}).get('rvcontinue')
    if not cont:
        break
    params['rvcontinue'] = cont
print(f"Total actual revisions fetched: {len(revisions)}")

# ─── FETCH SNAPSHOT METADATA ────────────────────────────────────────
print(f"Fetching snapshot metadata from '{SNAPSHOT_URL}'...")
resp = requests.get(SNAPSHOT_URL, params={'action': 'raw'})
if resp.status_code != 200:
    print("Failed to fetch snapshot page; skipping snapshot entries.")
    snapshots = []
else:
    raw = resp.text
    pattern = re.compile(
        r"^\|\s*(?P<id>\d+)\s*\|\|\s*(?P<ts>[^|]+?)\s*\|\|\s*(?P<user>[^|]+?)\s*\|\|\s*<nowiki>(?P<cm>.*?)</nowiki>",
        re.MULTILINE)
    snapshots = []
    for m in pattern.finditer(raw):
        snapshots.append({
            'revid': int(m.group('id')),
            'timestamp': m.group('ts').strip(),
            'user': m.group('user').strip(),
            'comment': m.group('cm').strip(),
            'content': ''
        })
print(f"Total snapshot entries parsed: {len(snapshots)}")

# ─── MERGE AND SORT ALL ENTRIES ─────────────────────────────────────
print("Merging actual revisions and snapshot entries by timestamp...")
from datetime import datetime
entries = []
for rev in revisions:
    entries.append({
        'revid': rev['revid'],
        'timestamp': rev['timestamp'],
        'user': rev.get('user', ''),
        'comment': rev.get('comment', ''),
        'content': rev.get('slots', {}).get('main', {}).get('*', rev.get('*', ''))
    })
for snap in snapshots:
    entries.append(snap)
entries.sort(key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')))

# ─── BUILD XML EXPORT FOR IMPORT ────────────────────────────────────
print("Building combined XML export...")
xml_lines = [
    '<?xml version="1.0"?>',
    '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xml:lang="en">',
    '<siteinfo/>',
    '<page>',
    f'  <title>{escape(PAGE_TITLE)}</title>'
]
for ent in entries:
    xml_lines.append('  <revision>')
    xml_lines.append(f'    <timestamp>{escape(ent["timestamp"])}</timestamp>')
    xml_lines.append('    <contributor>')
    xml_lines.append(f'      <username>{escape(ent["user"])}</username>')
    xml_lines.append('    </contributor>')
    xml_lines.append(f'    <comment>{escape(ent["comment"])}</comment>')
    xml_lines.append(f'    <id>{ent["revid"]}</id>')
    xml_lines.append(f'    <text xml:space="preserve">{escape(ent["content"])}</text>')
    xml_lines.append('  </revision>')
xml_lines.extend(['</page>', '</mediawiki>'])
xml_data = '\n'.join(xml_lines).encode('utf-8')
print(f"XML built ({len(xml_data)} bytes)")

# ─── IMPORT XML INTO SHINTO ─────────────────────────────────────────
print("Importing XML into Shinto with full history...")
token = site.get_token('csrf')
files = {'xml': ('export.xml', xml_data, 'text/xml')}
data = {
    'action': 'import',
    'format': 'json',
    'token': token,
    'fullhistory': '1',
    'interwikiprefix': 'en'
}
res = site.connection.post(API_URL, data=data, files=files, timeout=300).json()
if 'error' in res:
    err = res['error']
    print(f"Import error: {err.get('code')} - {err.get('info')}")
    sys.exit(1)
print("Import complete; full history and snapshots preserved.")

print("Done.")
