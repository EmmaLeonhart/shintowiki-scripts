"""
everybodywiki_import_bot.py (v9)
================================
Imports full revision history of a page from EverybodyWiki into Shinto Wiki,
plus snapshot metadata from its Edithistory page, preserving timestamps.

- Fetches API revisions
- Parses Edithistory table entries as empty-content revisions
- Merges and sorts by timestamp
- Builds XML, saves for debugging, and imports via MediaWiki import API
- Polls until the final timestamp is confirmed on Shinto Wiki

CONFIGURE at top and run:
  python everybodywiki_import_bot.py
"""

import sys
import time
import re
import requests
import mwclient
from xml.sax.saxutils import escape
from datetime import datetime
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
PAGE_TITLE    = 'Female_(gender)'  # EverybodyWiki title (underscores allowed)
RAW_TITLE     = PAGE_TITLE
LOCAL_TITLE   = PAGE_TITLE.replace('_', ' ')  # target page on Shinto

EWWIKI_API    = 'https://en.everybodywiki.com/api.php'
SNAPSHOT_PAGE = 'Edithistory:' + RAW_TITLE
SNAPSHOT_URL  = f'https://en.everybodywiki.com/{SNAPSHOT_PAGE}'

SHINTO_URL    = 'shinto.miraheze.org'
SHINTO_PATH   = '/w/'
API_URL       = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME      = 'Immanuelle'
PASSWORD      = '[REDACTED_SECRET_1]'
THROTTLE      = 1.0  # seconds between HTTP/API calls

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in to {SHINTO_URL} as {site.userinfo.get('name')}")

# ─── FETCH API REVISIONS ───────────────────────────────────────────
print(f"Fetching revisions for '{RAW_TITLE}' from EverybodyWiki...")
revisions = []
params = {
    'action': 'query', 'format': 'json', 'prop': 'revisions',
    'rvprop': 'ids|timestamp|user|comment|content', 'rvslots': 'main',
    'rvlimit': 'max', 'rvdir': 'newer', 'titles': RAW_TITLE
}
while True:
    r = requests.get(EWWIKI_API, params=params)
    r.raise_for_status()
    data = r.json()
    pages = data.get('query', {}).get('pages', {})
    info = next(iter(pages.values()), {})
    revs = info.get('revisions', [])
    if not revs:
        print("No revisions found; exiting.")
        sys.exit(1)
    revisions.extend(revs)
    cont = data.get('continue', {}).get('rvcontinue')
    if not cont:
        break
    params['rvcontinue'] = cont
    time.sleep(THROTTLE)
print(f"Fetched {len(revisions)} actual revisions.")

# ─── FETCH SNAPSHOT ENTRIES ────────────────────────────────────────
print(f"Fetching snapshot metadata from '{SNAPSHOT_URL}'...")
r = requests.get(SNAPSHOT_URL, params={'action':'raw'}, timeout=30)
if r.status_code != 200:
    print("Snapshot page unavailable; skipping snapshots.")
    snapshots = []
else:
    raw = r.text
    pat = re.compile(
        r"^\|\s*(?P<id>\d+)\s*\|\|\s*(?P<ts>[^|]+?)\s*\|\|\s*(?P<user>[^|]+?)\s*\|\|\s*<nowiki>(?P<cm>.*?)</nowiki>",
        re.MULTILINE
    )
    snapshots = []
    for m in pat.finditer(raw):
        snapshots.append({
            'revid': int(m.group('id')),
            'timestamp': m.group('ts').strip(),
            'user': m.group('user').strip(),
            'comment': m.group('cm').strip(),
            'content': ''
        })
print(f"Parsed {len(snapshots)} snapshot entries.")

# ─── MERGE & SORT ALL ENTRIES ──────────────────────────────────────
print("Merging and sorting all entries by timestamp...")
entries = []
# actual
for rv in revisions:
    entries.append({
        'timestamp': rv['timestamp'],
        'user': rv.get('user', ''),
        'comment': rv.get('comment', ''),
        'revid': rv['revid'],
        'content': rv.get('slots', {}).get('main', {}).get('*', '')
    })
# snapshots
entries.extend(snapshots)
# sort
entries.sort(key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')))

# ─── BUILD XML FOR IMPORT ──────────────────────────────────────────
print("Building combined XML export...")
xml_lines = [
    '<?xml version="1.0"?>',
    '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xml:lang="en">',
    '<siteinfo/>',
    '<page>',
    f'  <title>{escape(LOCAL_TITLE)}</title>'
]
for ent in entries:
    xml_lines.extend([
        '  <revision>',
        f'    <timestamp>{escape(ent["timestamp"])}</timestamp>',
        '    <contributor>',
        f'      <username>{escape(ent["user"])}</username>',
        '    </contributor>',
        f'    <comment>{escape(ent["comment"])}</comment>',
        f'    <id>{ent["revid"]}</id>',
        f'    <text xml:space="preserve">{escape(ent["content"])}</text>',
        '  </revision>'
    ])
xml_lines.extend(['</page>', '</mediawiki>'])
xml_data = '\n'.join(xml_lines).encode('utf-8')

# ─── SAVE XML TO FILE FOR DEBUG ─────────────────────────────────────
with open('export.xml', 'wb') as xml_file:
    xml_file.write(xml_data)
print(f"XML written to export.xml ({len(xml_data)} bytes) for inspection.")

# ─── IMPORT XML INTO SHINTO ─────────────────────────────────────────
print("Uploading XML import to Shinto...")
token = site.get_token('csrf')
files = {'xml': ('export.xml', xml_data, 'text/xml')}
data = {
    'action': 'import',
    'format': 'json',
    'token': token,
    'fullhistory': '1',
    'interwikiprefix': 'en'
}
r = site.connection.post(API_URL, data=data, files=files, timeout=300)
res = r.json()
if 'error' in res:
    err = res['error']
    print(f"Import failed: {err['code']} - {err['info']}")
    sys.exit(1)
print("Import request accepted.")

# ─── WAIT FOR FINAL TIMESTAMP ───────────────────────────────────────
final_ts = entries[-1]['timestamp']
print(f"Waiting for final timestamp {final_ts} on Shinto page '{LOCAL_TITLE}'...")
while True:
    info = site.api(
        'query', prop='revisions', titles=LOCAL_TITLE,
        rvprop='timestamp', rvlimit=1, format='json'
    )
    page = next(iter(info['query']['pages'].values()))
    revs = page.get('revisions') or []
    cur_ts = revs[0]['timestamp'] if revs else None
    if cur_ts == final_ts:
        print("Final revision confirmed on Shinto.")
        break
    print(f"Still waiting... current top ts {cur_ts}")
    time.sleep(5)
print("Done importing full history.")
