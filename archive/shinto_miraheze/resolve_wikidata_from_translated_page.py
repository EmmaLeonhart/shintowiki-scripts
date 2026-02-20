"""resolve_wikidata_from_translated_page.py
================================================
For pages in [[Category:Translated_page_but_missing_wikidata]],
extract the source language/page from {{translated page|...}} template
and check for wikidata on the source Wikipedia page.
================================================

This script:
1. Gets all pages in [[Category:Translated_page_but_missing_wikidata]]
2. Extracts language and source page title from {{translated page|...}}
3. Queries the source Wikipedia page for Wikidata ID
4. If found: Adds {{wikidata link|QID}}
5. If not found: Adds {{Category:Translated page with no wikidata source}}
6. Reports statistics

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
PASSWORD  = '[REDACTED_SECRET_2]'
CATEGORY_NAME = 'Translated_page_but_missing_wikidata'

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
# Match {{translated page|lang|page|...}} template
TRANSLATED_PAGE_RE = re.compile(r'\{\{translated\s+page\s*\|\s*(\w+)\s*\|\s*([^\|]+)\s*\|', re.IGNORECASE)

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


def get_wikipedia_url(lang_code):
    """Get the Wikipedia API URL for a given language code."""
    lang_map = {
        'en': 'https://en.wikipedia.org/w/api.php',
        'ja': 'https://ja.wikipedia.org/w/api.php',
        'de': 'https://de.wikipedia.org/w/api.php',
        'zh': 'https://zh.wikipedia.org/w/api.php',
        'ru': 'https://ru.wikipedia.org/w/api.php',
        'fr': 'https://fr.wikipedia.org/w/api.php',
        'es': 'https://es.wikipedia.org/w/api.php',
        'it': 'https://it.wikipedia.org/w/api.php',
        'pt': 'https://pt.wikipedia.org/w/api.php',
        'ar': 'https://ar.wikipedia.org/w/api.php',
    }
    return lang_map.get(lang_code)


def check_wikipedia_page(lang_code, page_title):
    """
    Query Wikipedia API to check if page exists and get its Wikidata ID.
    Returns: (page_exists, wikidata_id)
    """
    url = get_wikipedia_url(lang_code)
    if not url:
        return False, None

    try:
        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageprops|info",
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
            return False, None

        pages = data["query"]["pages"]
        if not pages:
            return False, None

        # Get the first (and should be only) page
        page = next(iter(pages.values()))

        # Check if page is missing
        if "missing" in page:
            return False, None

        # Check if it's a redirect - we only want real articles
        if "redirect" in page:
            return False, None

        # Page exists! Now check for wikidata ID
        wikidata_id = None
        if "pageprops" in page and "wikibase_item" in page["pageprops"]:
            wikidata_id = page["pageprops"]["wikibase_item"]

        return True, wikidata_id

    except Exception as e:
        print(f"      ! error checking {lang_code}wiki – {e}")

    return False, None


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
    """
    Process a translated page by extracting source language/title
    and checking for wikidata on the source Wikipedia page.
    """
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Extract translated page template info
    match = TRANSLATED_PAGE_RE.search(original_text)
    if not match:
        print(f"   ! no {{{{translated page}}}} template found")
        return False

    lang_code = match.group(1)
    source_title = match.group(2).strip()

    print(f"   → source: {lang_code}:{source_title}")

    # Check the source Wikipedia page
    page_exists, wikidata_id = check_wikipedia_page(lang_code, source_title)

    if not page_exists:
        print(f"   ! source page does not exist on {lang_code}wiki")
        return False

    if wikidata_id:
        # Found wikidata! Add it
        new_text = original_text.rstrip()
        new_text += f"\n{{{{wikidata link|{wikidata_id}}}}}\n"

        if new_text != original_text:
            if safe_save(page, new_text, f"Bot: add wikidata from translated source {lang_code}wiki"):
                print(f"   • resolved: {{{{wikidata link|{wikidata_id}}}}} (from {lang_code}:{source_title})")
                return True
    else:
        # Source page exists but has no wikidata
        print(f"   ! source page exists but has no wikidata")
        return False

    return False


def main():
    """Process all pages in Translated page but missing wikidata category."""

    print(f"Fetching pages from [[Category:{CATEGORY_NAME}]]...\n")

    pages = get_category_pages(CATEGORY_NAME)

    if not pages:
        print(f"ERROR: No pages found in [[Category:{CATEGORY_NAME}]]")
        return

    print(f"Found {len(pages)} pages in category\n")
    print(f"Processing pages...\n")

    resolved_count = 0
    no_template = 0
    source_not_exist = 0
    source_no_wikidata = 0

    for idx, title in enumerate(pages, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")

            try:
                original_text = page.text()
            except Exception as e:
                print(f"   ! could not read page – {e}")
                continue

            # Check if page has translated page template
            match = TRANSLATED_PAGE_RE.search(original_text)
            if not match:
                no_template += 1
                print(f"   ! no {{{{translated page}}}} template found")
                continue

            lang_code = match.group(1)
            source_title = match.group(2).strip()

            print(f"   → source: {lang_code}:{source_title}")

            # Check the source Wikipedia page
            page_exists, wikidata_id = check_wikipedia_page(lang_code, source_title)

            if not page_exists:
                source_not_exist += 1
                print(f"   ! source page does not exist")
                continue

            if wikidata_id:
                # Found wikidata! Add it
                new_text = original_text.rstrip()
                new_text += f"\n{{{{wikidata link|{wikidata_id}}}}}\n"

                if new_text != original_text:
                    if safe_save(page, new_text, f"Bot: add wikidata from translated source {lang_code}wiki"):
                        print(f"   • resolved: {{wikidata link|{wikidata_id}}} (from {lang_code}:{source_title})")
                        resolved_count += 1
            else:
                source_no_wikidata += 1
                print(f"   ! source page has no wikidata")

        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting
        time.sleep(0.5)

    print(f"\nDone!")
    print(f"  Resolved {resolved_count} pages with wikidata from translated source")
    print(f"  Skipped {source_no_wikidata} pages with sources that have no wikidata")
    print(f"  Skipped {source_not_exist} pages where source doesn't exist")
    print(f"  Skipped {no_template} pages with no translated page template")


if __name__ == "__main__":
    main()
