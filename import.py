"""
everybodywiki_import_bot.py (v11)
================================
Batch-import full revision histories from EverybodyWiki into Shinto Wiki,
using interwiki links of the form [[every:TITLE]].

- Reads local page titles from pages.txt
- For each page, finds [[every:…]] link to get EverybodyWiki title
- Fetches API revisions + Edithistory snapshots
- Merges, sorts, builds XML with siteinfo
- Saves export_<local>.xml for debugging
- Imports via MediaWiki import API
- Optionally polls for final timestamp

CONFIGURE:
  USERNAME/PASSWORD for Shinto
  THROTTLE delay between HTTP/API calls

Run:
  python everybodywiki_import_bot.py
"""

import os
import sys
import time
import re
import requests
import mwclient
from xml.sax.saxutils import escape
from datetime import datetime
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
PAGES_TXT     = 'pages.txt'
EWWIKI_API    = 'https://en.everybodywiki.com/api.php'
SHINTO_URL    = 'shinto.miraheze.org'
SHINTO_PATH   = '/w/'
API_URL       = f'https://{SHINTO_URL}{SHINTO_PATH}api.php'
USERNAME      = 'Immanuelle'
PASSWORD      = '[REDACTED_SECRET_1]'
THROTTLE      = 1.0  # seconds between HTTP/API calls

# ─── PATTERN ────────────────────────────────────────────────────────
EVERY_LINK_RE = re.compile(r"\[\[\s*every:([^\]|]+)")

# ─── LOAD TITLES ───────────────────────────────────────────────────
def load_titles():
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT, 'w', encoding='utf-8').close()
        print(f"Created empty {PAGES_TXT}; add local page titles and re-run.")
        sys.exit()
    with open(PAGES_TXT, 'r', encoding='utf-8') as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

# ─── LOGIN TO SHINTO ───────────────────────────────────────────────
site = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in to {SHINTO_URL} as {site.userinfo.get('name')}")

# ─── PROCESS ONE PAGE ──────────────────────────────────────────────
def process_page(local):
    print(f"\n=== Processing '{local}' ===")
    text = ''
    try:
        text = site.pages[local].text()
    except Exception:
        print(f"Local page '{local}' missing; skipping.")
        return
    m = EVERY_LINK_RE.search(text)
    if not m:
        print("No [[every:…]] link found; skipping.")
        return
    raw = m.group(1).strip()
    ew_title = raw.replace(' ', '_')
    print(f"Found interwiki to EverybodyWiki: '{ew_title}'")

    # fetch API revisions
    revisions = []
    params = {
        'action':'query','format':'json','prop':'revisions',
        'rvprop':'ids|timestamp|user|comment|content','rvslots':'main',
        'rvlimit':'max','rvdir':'newer','titles':ew_title
    }
    print("Fetching API revisions...")
    while True:
        r = requests.get(EWWIKI_API, params=params)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        info = next(iter(pages.values()), {})
        revs = info.get('revisions', [])
        if not revs:
            print("No revisions found on EverybodyWiki; skipping.")
            return
        revisions.extend(revs)
        cont = data.get('continue', {}).get('rvcontinue')
        if not cont:
            break
        params['rvcontinue'] = cont
        time.sleep(THROTTLE)
    print(f"Fetched {len(revisions)} revisions.")

    # fetch snapshots
    snap_url = f'https://en.everybodywiki.com/Edithistory:{ew_title}'
    print(f"Fetching snapshot metadata: {snap_url}")
    r = requests.get(snap_url, params={'action':'raw'}, timeout=30)
    snapshots = []
    if r.status_code == 200:
        raw_src = r.text
        pat = re.compile(r"^\|\s*(?P<id>\d+)\s*\|\|\s*(?P<ts>[^|]+?)\s*\|\|\s*(?P<user>[^|]+?)\s*\|\|\s*<nowiki>(?P<cm>.*?)</nowiki>", re.MULTILINE)
        for m2 in pat.finditer(raw_src):
            snapshots.append({
                'revid':int(m2.group('id')),
                'timestamp':m2.group('ts').strip(),
                'user':m2.group('user').strip(),
                'comment':m2.group('cm').strip(),
                'content':''
            })
    print(f"Parsed {len(snapshots)} snapshot entries.")

    # merge + sort
    entries = [{
        'timestamp':rv['timestamp'],'user':rv.get('user',''),
        'comment':rv.get('comment',''),'revid':rv['revid'],
        'content':rv.get('slots',{}).get('main',{}).get('*','')
    } for rv in revisions] + snapshots
    entries.sort(key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')))

    # build XML
    print("Building XML export...")
    xml = [
        '<?xml version="1.0"?>',
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/"',
        '            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '            xsi:schemaLocation="http://www.mediawiki.org/xml/export-0.11/ ',
        '            http://www.mediawiki.org/xml/export-0.11.xsd"',
        '            version="0.11" xml:lang="en">',
        '<siteinfo>',
        '  <sitename>Shinto Wiki</sitename>',
        '  <dbname>shintowiki</dbname>',
        '  <base>https://shinto.miraheze.org/wiki/Main_Page</base>',
        '  <case>first-letter</case>',
        '  <namespaces>...same as v10...</namespaces>',
        '</siteinfo>',
        '<page>', f'  <title>{escape(local)}</title>'
    ]
    for ent in entries:
        xml.extend([
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
    xml.extend(['</page>','</mediawiki>'])
    data_bytes = '\n'.join(xml).encode('utf-8')

    # save debug
    fname = f'export_{local.replace(" ","_")}.xml'
    with open(fname, 'wb') as f:
        f.write(data_bytes)
    print(f"Saved XML to {fname}")

    # import
    print("Importing into Shinto...")
    token = site.get_token('csrf')
    res = site.connection.post(API_URL,
        data={'action':'import','format':'json','token':token,'fullhistory':'1','interwikiprefix':'en'},
        files={'xml':(fname,data_bytes,'text/xml')}, timeout=300)
    j = res.json()
    if 'error' in j:
        print(f"Import error on '{local}': {j['error']['info']}")
    else:
        print(f"Import accepted for '{local}'.")
    time.sleep(THROTTLE)

# ─── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    titles = load_titles()
    for t in titles:
        process_page(t)
    print("All done.")

if __name__=='__main__':
    main()
