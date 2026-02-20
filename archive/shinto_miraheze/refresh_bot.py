"""
wiki_export_import_bot.py
=========================
For each page title in pages.txt:
 1. Fetch the **current revision** XML (no history) from English Wikipedia via Special:Export (`history=0`).
 2. Strip out all `<timestamp>` elements.
 3. Replace or insert `<comment>Imported from wikipedia at YYYY-MM-DD HH:MM:SS on [[PageTitle]]</comment>` in that revision.
 4. Import the modified XML into Shinto Wiki via the import API (`interwikiprefix=en`).
 5. Query the enwiki API for transcluded templates (`prop=templates`) and for each template import its current revision (no history) the same way.

Configure credentials and list page titles in pages.txt, then run:
    python wiki_export_import_bot.py
"""
import os
import sys
import time
import re
from datetime import datetime
import requests
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE   = 'refresh.txt'
SHINTO_HOST  = 'shinto.miraheze.org'
SHINTO_PATH  = '/w/'
SHINTO_USER  = 'Immanuelle'
SHINTO_PASS  = '[REDACTED_SECRET_2]'
THROTTLE     = 1.0            # seconds between operations
TIME_FORMAT  = '%Y-%m-%d %H:%M:%S'
EXPORT_URL   = 'https://en.wikipedia.org/wiki/Special:Export'
ENWIKI_HOST  = 'en.wikipedia.org'
ENWIKI_PATH  = '/w/'

# ─── LOAD PAGE TITLES ─────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add page titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

# ─── FETCH AND MODIFY XML ─────────────────────────────────────────
def fetch_and_patch_xml(title):
    # Export only the current revision
    resp = requests.post(EXPORT_URL, data={'pages': title, 'history': '0'})
    resp.raise_for_status()
    xml = resp.text
    # Remove timestamp tags
    xml = re.sub(r'<timestamp>.*?</timestamp>', '', xml)
    # Insert or replace comment tag with page context
    now = datetime.now().strftime(TIME_FORMAT)
    comment = f'<comment>Imported from wikipedia at {now} on [[{title}]]</comment>'
    def repl(match):
        rev = match.group(0)
        if '<comment>' in rev:
            return re.sub(r'<comment>.*?</comment>', comment, rev)
        return rev.replace('</revision>', f'    {comment}\n  </revision>')
    xml = re.sub(r'<revision>[\s\S]*?</revision>', repl, xml, count=1)
    return xml.encode('utf-8')

# ─── IMPORT XML INTO SHINTO ───────────────────────────────────────
def import_xml(site, api_url, token, xml_data, title):
    files = {'xml': ('export.xml', xml_data, 'text/xml')}
    data = {'action': 'import', 'format': 'json', 'token': token, 'interwikiprefix': 'en'}
    try:
        res = site.connection.post(api_url, data=data, files=files, timeout=300).json()
        if 'error' in res:
            err = res['error']
            print(f"  ! Import error for [[{title}]]: {err['code']} - {err['info']}")
            return False
        print(f"  ✓ Imported [[{title}]]")
        return True
    except APIError as e:
        print(f"  ! APIError importing [[{title}]]: {e.code}")
    except Exception as e:
        print(f"  ! Exception importing [[{title}]]: {e}")
    return False

# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    titles = load_titles(PAGES_FILE)
    if not titles:
        print("No pages to process.")
        return
    # connect to Shinto
    shinto = mwclient.Site(SHINTO_HOST, path=SHINTO_PATH)
    shinto.login(SHINTO_USER, SHINTO_PASS)
    token = shinto.get_token('csrf')
    api_url = f'https://{SHINTO_HOST}{SHINTO_PATH}api.php'
    # connect to enwiki for templates prop
    enwiki = mwclient.Site(ENWIKI_HOST, path=ENWIKI_PATH)

    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{len(titles)} → [[{title}]]")
        # import main page
        try:
            xml_main = fetch_and_patch_xml(title)
            import_xml(shinto, api_url, token, xml_main, title)
        except Exception as e:
            print(f"  ! Failed main export [[{title}]]: {e}")
            continue
        time.sleep(THROTTLE)
        # fetch transcluded templates via API
        print(" → fetching transcluded templates...")
        try:
            tpl_list = []
            q = enwiki.api('query', titles=title, prop='templates', tpllimit='max')
            pages = q.get('query', {}).get('pages', {})
            for p in pages.values():
                for tpl in p.get('templates', []):
                    tpl_title = tpl['title']
                    tpl_list.append(tpl_title)
        except Exception as e:
            print(f"  ! Failed to get templates for [[{title}]]: {e}")
            tpl_list = []
        # import each template
        for tpl_title in tpl_list:
            print(f"  → [[{tpl_title}]]")
            try:
                xml_tpl = fetch_and_patch_xml(tpl_title)
                import_xml(shinto, api_url, token, xml_tpl, tpl_title)
            except Exception as e:
                print(f"    ! Failed export [[{tpl_title}]]: {e}")
            time.sleep(THROTTLE)

    print("All done.")

if __name__ == '__main__':
    main()
