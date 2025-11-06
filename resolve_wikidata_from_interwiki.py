"""resolve_wikidata_from_interwiki.py
================================================
For Missing wikidata pages with enwiki/jawiki/dewiki links, find wikidata and link it.
================================================

This script:
1. Gets all pages in [[Category:Missing wikidata]]
2. For each page, looks for [[en:...]], [[ja:...]], or [[de:...]] interwiki links
3. Queries the linked Wikipedia page to find its Wikidata ID
4. Removes [[Category:Missing wikidata]] and adds {{wikidata link|QID}}
5. Reports statistics

"""

import time
import re
import mwclient
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
PASSWORD  = '[REDACTED_SECRET_1]'
CATEGORY_NAME = 'Missing wikidata'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")

# ─── REGEX PATTERNS ─────────────────────────────────────────
# Match [[en:...]], [[ja:...]], and [[de:...]] interwiki links
EN_INTERWIKI_RE = re.compile(r'\[\[en:([^\]]+)\]\]')
JA_INTERWIKI_RE = re.compile(r'\[\[ja:([^\]]+)\]\]')
DE_INTERWIKI_RE = re.compile(r'\[\[de:([^\]]+)\]\]')

# Match the missing wikidata category
MISSING_CATEGORY_RE = re.compile(r'\[\[Category:' + re.escape(CATEGORY_NAME) + r'\]\]')

# ─── HELPERS ─────────────────────────────────────────────────

def get_category_pages(category_name):
    """Get all pages in a category using the API."""
    pages = []
    params = {
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': f'Category:{category_name}',
        'cmlimit': 500,
        'cmtype': 'page',
        'format': 'json'
    }

    while True:
        try:
            response = requests.get(
                f'https://{WIKI_URL}{WIKI_PATH}api.php',
                params=params,
                headers={'User-Agent': 'Shinto Wiki Bot (https://shinto.miraheze.org/)'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if 'query' not in data or 'categorymembers' not in data['query']:
                break

            for member in data['query']['categorymembers']:
                pages.append(member['title'])

            if 'continue' not in data:
                break
            params['cmcontinue'] = data['continue']['cmcontinue']
        except Exception as e:
            print(f"Error fetching category members: {e}")
            break

    return pages


def get_wikidata_from_wikipedia(wiki, page_title):
    """Query Wikipedia API to find Wikidata ID for a page."""
    try:
        if wiki == 'en':
            url = "https://en.wikipedia.org/w/api.php"
        elif wiki == 'ja':
            url = "https://ja.wikipedia.org/w/api.php"
        elif wiki == 'de':
            url = "https://de.wikipedia.org/w/api.php"
        else:
            return None

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "format": "json"
        }
        headers = {
            "User-Agent": "Shinto Wiki Bot (https://shinto.miraheze.org/)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "query" not in data or "pages" not in data["query"]:
            return None

        pages = data["query"]["pages"]
        if not pages:
            return None

        # Get the first (and should be only) page
        page = next(iter(pages.values()))

        # Check for wikidata ID in pageprops
        if "pageprops" in page and "wikibase_item" in page["pageprops"]:
            return page["pageprops"]["wikibase_item"]
    except Exception as e:
        print(f"      ! error checking {wiki}wiki – {e}")

    return None


def safe_save(page, text, summary):
    """Attempt Page.save but gracefully back off on edit-conflict."""
    if not page.exists:
        print(f"   • skipped save, page [[{page.name}]] no longer exists")
        return False

    # Nothing to do if text hasn't changed
    try:
        current = page.text()
    except Exception:
        current = None
    if current is not None and current.rstrip() == text.rstrip():
        return False

    try:
        page.save(text, summary=summary)
        return True
    except mwclient.errors.EditError as e:
        if getattr(e, "code", "") == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
    except mwclient.errors.APIError as e:
        if e.code == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
    except Exception as e:
        print(f"   ! Save failed on [[{page.name}]] – {e}")
        return False


def process_page(page):
    """Process a single page to resolve wikidata from interwiki links."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check for enwiki, jawiki, and dewiki interwiki links
    en_match = EN_INTERWIKI_RE.search(original_text)
    ja_match = JA_INTERWIKI_RE.search(original_text)
    de_match = DE_INTERWIKI_RE.search(original_text)

    wikidata_id = None
    wiki_used = None

    if en_match:
        en_title = en_match.group(1)
        wikidata_id = get_wikidata_from_wikipedia('en', en_title)
        if wikidata_id:
            wiki_used = 'en'

    if not wikidata_id and ja_match:
        ja_title = ja_match.group(1)
        wikidata_id = get_wikidata_from_wikipedia('ja', ja_title)
        if wikidata_id:
            wiki_used = 'ja'

    if not wikidata_id and de_match:
        de_title = de_match.group(1)
        wikidata_id = get_wikidata_from_wikipedia('de', de_title)
        if wikidata_id:
            wiki_used = 'de'

    if not wikidata_id:
        return False

    # Found wikidata! Remove category and add template
    new_text = MISSING_CATEGORY_RE.sub('', original_text)
    new_text = new_text.rstrip()
    new_text += f"\n{{{{wikidata link|{wikidata_id}}}}}\n"

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: resolve wikidata from {wiki_used}wiki interwiki"):
            print(f"   • resolved: [[{page.name}]] → {wikidata_id} (from {wiki_used}wiki)")
            return True

    return False


def main():
    """Process all pages in Missing wikidata category."""

    print(f"Fetching pages from [[Category:{CATEGORY_NAME}]]...\n")

    pages = get_category_pages(CATEGORY_NAME)

    if not pages:
        print(f"ERROR: No pages found in [[Category:{CATEGORY_NAME}]]")
        return

    print(f"Found {len(pages)} pages in category\n")
    print(f"Processing pages...\n")

    resolved_count = 0
    no_interwiki = 0
    no_wikidata = 0

    for idx, title in enumerate(pages, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")

            try:
                original_text = page.text()
            except Exception as e:
                print(f"   ! could not read page – {e}")
                continue

            # Check if has interwiki links
            en_match = EN_INTERWIKI_RE.search(original_text)
            ja_match = JA_INTERWIKI_RE.search(original_text)
            de_match = DE_INTERWIKI_RE.search(original_text)

            if not en_match and not ja_match and not de_match:
                no_interwiki += 1
                continue

            # Has interwiki, try to resolve
            if process_page(page):
                resolved_count += 1
            else:
                no_wikidata += 1

        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting
        time.sleep(0.5)

    print(f"\nDone!")
    print(f"  Resolved {resolved_count} pages with wikidata from interwiki")
    print(f"  Skipped {no_interwiki} pages without enwiki/jawiki/dewiki interwikis")
    print(f"  Tried {no_wikidata} pages with interwikis but no wikidata found")


if __name__ == "__main__":
    main()
