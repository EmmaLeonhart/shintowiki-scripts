"""
everybodywiki_import_bot.py (v5)
================================
Imports approximate full revision history of a page from EverybodyWiki into Shinto Wiki by:
  • Fetching actual revisions and snapshot metadata
  • Merging them by timestamp
  • Building an XML history where snapshot entries duplicate the previous content
    with the correct username/timestamp/comment
  • Importing via the API to preserve timestamps and authors

Configure PAGE_TITLE, adjust credentials, then run:
  python everybodywiki_import_bot.py
"""

import sys
import time
import re
import requests
import mwclient
from datetime import datetime, timezone
from xml.sax.saxutils import escape

# ─── CONFIG ─────────────────────────────────────────────────────────
EWWIKI_API    = 'https://en.everybodywiki.com/api.php'
SHINTO_URL    = 'shinto.miraheze.org'
SHINTO_PATH   = '/w/'
API_URL       = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME      = 'Immanuelle'
PASSWORD      = '[REDACTED_SECRET_1]'
PAGE_TITLE    = 'Superstitions_in_Christian_societies'
SNAPSHOT_PAGE = f'Edithistory:{PAGE_TITLE}'
THROTTLE      = 1.0  # seconds between API calls

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in to Shinto as {site.userinfo.get('name')}.")

# ─── FETCH ACTUAL REVISIONS VIA API ─────────────────────────────────
print(f"Fetching actual revisions for '{PAGE_TITLE}'...")
actual = []
params = {
    'action': 'query', 'format': 'json', 'prop': 'revisions',
    'rvprop': 'ids|timestamp|user|comment|content', 'rvslots': 'main',
    'rvlimit': 'max', 'rvdir': 'newer', 'titles': PAGE_TITLE
}
while True:
    r = requests.get(EWWIKI_API, params=params)
    r.raise_for_status()
    data = r.json()
    pages = data.get('query', {}).get('pages', {})
    pg = next(iter(pages.values()), {})
    revs = pg.get('revisions', [])
    if not revs:
        print(f"No actual revisions for '{PAGE_TITLE}'.")
        sys.exit(1)
    actual.extend(revs)
    cont = data.get('continue', {}).get('rvcontinue')
    if not cont:
        break
    params['rvcontinue'] = cont
print(f"Fetched {len(actual)} actual revisions.")

# ─── FETCH SNAPSHOT METADATA ────────────────────────────────────────
print(f"Fetching snapshot metadata from '{SNAPSHOT_PAGE}'...")
raw = requests.get(
    f'https://en.everybodywiki.com/wiki/{SNAPSHOT_PAGE}',
    params={'action': 'raw'}, timeout=60
).text
# Parse table rows
snapshots = []
pattern = re.compile(r"^\|\s*(?P<id>\d+)\s*\|\|\s*(?P<ts>[^|]+?)\s*\|\|\s*(?P<user>[^|]+?)\s*\|\|\s*<nowiki>(?P<cm>.*?)</nowiki>")
for line in raw.splitlines():
    m = pattern.match(line)
    if m:
        snapshots.append({
            'revid': int(m.group('id')),
            'timestamp': m.group('ts'),
            'user': m.group('user'),
            'comment': m.group('cm'),
            'content': None
        })
print(f"Parsed {len(snapshots)} snapshot entries.")

# ─── MERGE BY TIMESTAMP ─────────────────────────────────────────────
print("Merging revisions and snapshots by timestamp...")
# Convert actual to unified format
entries = []
for rev in actual:
    ts = rev['timestamp']
    entries.append({
        'timestamp': ts,
        'revid': rev['revid'],
        'user': rev.get('user', ''),
        'comment': rev.get('comment', ''),
        'content': rev.get('slots', {}).get('main', {}).get('*', rev.get('*', ''))
    })
# Add snapshot entries
entries.extend(snapshots)
# Sort by timestamp
def parse_ts(x):
    return datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00'))
entries.sort(key=parse_ts)

# ─── BUILD XML FOR IMPORT ──────────────────────────────────────────
print("Building combined XML export...")
xml = ['<?xml version="1.0"?>',
       '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xml:lang="en">',
       '<siteinfo/>',
       '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xml:lang="en">',
       '<page>', f'  <title>{escape(PAGE_TITLE)}</title>']
last_text = ''
for ent in entries:
    text = ent['content'] if ent['content'] is not None else last_text
    last_text = text
    xml.append('  <revision>')
    xml.append(f'    <timestamp>{escape(ent["timestamp"])}</timestamp>')
    xml.append('    <contributor>')
    xml.append(f'      <username>{escape(ent["user"])}</username>')
    xml.append('    </contributor>')
    xml.append(f'    <comment>{escape(ent["comment"])}</comment>')
    xml.append(f'    <id>{ent["revid"]}</id>')
    xml.append(f'    <text xml:space="preserve">{escape(text)}</text>')
    xml.append('  </revision>')
xml.append('</page>')
xml.append('</mediawiki>')
xml_data = '\n'.join(xml).encode('utf-8')
print(f"XML ready ({len(xml_data)} bytes)")

# ─── IMPORT XML INTO SHINTO ─────────────────────────────────────────
print("Importing into Shinto...")
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
        e = res['error']
        print(f"Import error: {e['code']} – {e['info']}")
        sys.exit(1)
    print("Import successful. History with snapshots added.")
except Exception as e:
    print(f"Failed import: {e}")
    sys.exit(1)

print("Done.")
