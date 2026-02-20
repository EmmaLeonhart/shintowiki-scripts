"""Test processing a single category page"""

import mwclient
import re
import time
import requests
import sys

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in successfully\n")

# Get the specific page
page = site.pages['Category:1004 establishments']
print(f"Processing [[{page.name}]]")

try:
    text = page.text()
except Exception as e:
    print(f"ERROR reading page: {e}")
    sys.exit(1)

print(f"Page text length: {len(text)} chars")
print(f"\nFirst 500 chars:\n{text[:500]}\n")

# Extract interwiki links
INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')
interwikis_raw = INTERWIKI_RE.findall(text)

# Strip namespace prefixes
interwikis = []
for lang, title in interwikis_raw:
    if title.lower().startswith('category:'):
        title = title[9:]
    interwikis.append((lang, title))
print(f"Found {len(interwikis)} interwiki links:")
for lang, title in interwikis[:5]:
    print(f"  - {lang}:{title}")
if len(interwikis) > 5:
    print(f"  ... and {len(interwikis) - 5} more")

# Try querying Wikipedia for the first interwiki
if interwikis:
    lang_code, category_title = interwikis[0]
    print(f"\n\nTesting query for [[{lang_code}:Category:{category_title}]]")

    normalized_title = category_title.replace(' ', '_')
    url = f"https://{lang_code}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"Category:{normalized_title}",
        "prop": "pageprops",
        "format": "json"
    }
    headers = {
        "User-Agent": "WikidataBot/1.0 (https://shinto.miraheze.org/; bot for adding wikidata links)"
    }

    print(f"URL: {url}")
    print(f"Params: {params}")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")

        data = response.json()
        print(f"\nResponse (truncated):")
        if "query" in data and "pages" in data["query"]:
            for page_id, page_data in data["query"]["pages"].items():
                print(f"  Page ID: {page_id}")
                if "pageprops" in page_data and "wikibase_item" in page_data["pageprops"]:
                    print(f"  -> Wikidata: {page_data['pageprops']['wikibase_item']}")
                else:
                    print(f"  -> No wikidata found")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
