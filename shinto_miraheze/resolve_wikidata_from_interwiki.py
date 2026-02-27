"""resolve_wikidata_from_interwiki.py
================================================
For Missing wikidata pages with interwiki links, find wikidata and link it.
Also tags pages with interwiki links that exist but have no connected wikidata.
================================================

This script:
1. Gets all pages in [[Category:Missing wikidata]]
2. For each page, looks for [[en:...]], [[ja:...]], [[de:...]], [[zh:...]], or [[ru:...]] interwiki links
3. Verifies the foreign Wikipedia page actually EXISTS
4. If found with wikidata: Removes [[Category:Missing wikidata]] and adds {{wikidata link|QID}}
5. If foreign page exists but no wikidata: Adds [[Category:Foreign language page not connected to wikidata]] (keeps Missing wikidata category)
6. Does NOT modify pages where foreign Wikipedia link doesn't exist or is a redirect
7. Reports statistics

"""

import os
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
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
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
# Match [[en:...]], [[ja:...]], [[de:...]], [[zh:...]], and [[ru:...]] interwiki links
EN_INTERWIKI_RE = re.compile(r'\[\[en:([^\]]+)\]\]')
JA_INTERWIKI_RE = re.compile(r'\[\[ja:([^\]]+)\]\]')
DE_INTERWIKI_RE = re.compile(r'\[\[de:([^\]]+)\]\]')
ZH_INTERWIKI_RE = re.compile(r'\[\[zh:([^\]]+)\]\]')
RU_INTERWIKI_RE = re.compile(r'\[\[ru:([^\]]+)\]\]')

# Match the missing wikidata category
MISSING_CATEGORY_RE = re.compile(r'\[\[Category:' + re.escape(CATEGORY_NAME) + r'\]\]')
# Match the foreign language not connected category
FOREIGN_NOT_CONNECTED_RE = re.compile(r'\[\[Category:Foreign language page not connected to wikidata\]\]')
# Match the no valid interwikis category
NO_VALID_INTERWIKIS_RE = re.compile(r'\[\[Category:no valid interwikis\]\]')

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


def check_wikipedia_page(wiki, page_title):
    """
    Query Wikipedia API to check if page exists and get its Wikidata ID.
    Returns: (page_exists, wikidata_id)
    - page_exists: True if the Wikipedia page exists (and is not a redirect to article space)
    - wikidata_id: The Wikidata ID if found, None otherwise
    """
    try:
        if wiki == 'en':
            url = "https://en.wikipedia.org/w/api.php"
        elif wiki == 'ja':
            url = "https://ja.wikipedia.org/w/api.php"
        elif wiki == 'de':
            url = "https://de.wikipedia.org/w/api.php"
        elif wiki == 'zh':
            url = "https://zh.wikipedia.org/w/api.php"
        elif wiki == 'ru':
            url = "https://ru.wikipedia.org/w/api.php"
        else:
            return False, None

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

        # Check if page is missing (has -1 as pageid)
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
        print(f"      ! error checking {wiki}wiki for '{page_title}' – {e}")

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
    Process a single page to:
    1. Find wikidata if connected foreign wiki page exists with wikidata
    2. Tag with 'Foreign language not connected' if foreign page exists but no wikidata
    3. Tag with 'no valid interwikis' if interwiki links exist but are all invalid/redirects
    Does NOT remove Missing wikidata category - only adds new categories
    """
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Find ALL interwiki links for each language (not just the first)
    en_matches = EN_INTERWIKI_RE.findall(original_text)
    ja_matches = JA_INTERWIKI_RE.findall(original_text)
    de_matches = DE_INTERWIKI_RE.findall(original_text)
    zh_matches = ZH_INTERWIKI_RE.findall(original_text)
    ru_matches = RU_INTERWIKI_RE.findall(original_text)

    wikidata_id = None
    wiki_used = None
    found_valid_foreign_page = False
    checked_any_interwiki = False

    # Check each language's interwiki links in order, looking for wikidata
    # For each language, try interwikis in order until we find one with wikidata
    interwiki_checks = [
        (en_matches, 'en'),
        (ja_matches, 'ja'),
        (de_matches, 'de'),
        (zh_matches, 'zh'),
        (ru_matches, 'ru'),
    ]

    for titles, wiki_code in interwiki_checks:
        if titles:
            checked_any_interwiki = True
            # Try each interwiki for this language
            for title in titles:
                page_exists, found_wikidata = check_wikipedia_page(wiki_code, title)

                if page_exists:
                    found_valid_foreign_page = True
                    # If this one has wikidata, use it and stop looking
                    if found_wikidata and not wikidata_id:
                        wikidata_id = found_wikidata
                        wiki_used = wiki_code
                        break  # Found wikidata for this language, move to next language
                    # Otherwise continue to next interwiki for this language

    # Case 1: Found wikidata - remove Missing wikidata and add template
    if wikidata_id:
        new_text = MISSING_CATEGORY_RE.sub('', original_text)
        new_text = new_text.rstrip()
        new_text += f"\n{{{{wikidata link|{wikidata_id}}}}}\n"

        if new_text != original_text:
            if safe_save(page, new_text, f"Bot: resolve wikidata from {wiki_used}wiki interwiki"):
                print(f"   • resolved: [[{page.name}]] → {wikidata_id} (from {wiki_used}wiki)")
                return True
        return False

    # Case 2: Found valid foreign page but NO wikidata - add category (keep Missing wikidata)
    if found_valid_foreign_page:
        # Check if already has the foreign language not connected category
        if FOREIGN_NOT_CONNECTED_RE.search(original_text):
            return False

        # Add new category without removing Missing wikidata
        new_text = original_text.rstrip()
        new_text += "\n[[Category:Foreign language page not connected to wikidata]]\n"

        if new_text != original_text:
            if safe_save(page, new_text, "Bot: tag foreign language page not connected to wikidata"):
                print(f"   • tagged: [[{page.name}]] (foreign wiki exists, no wikidata)")
                return True

    # Case 3: Has interwiki links but NONE of them are valid (all redirects/missing) - tag as no valid interwikis
    if checked_any_interwiki and not found_valid_foreign_page:
        # Check if already has the no valid interwikis category
        if NO_VALID_INTERWIKIS_RE.search(original_text):
            return False

        # Add new category
        new_text = original_text.rstrip()
        new_text += "\n[[Category:no valid interwikis]]\n"

        if new_text != original_text:
            if safe_save(page, new_text, "Bot: tag page with no valid interwiki links"):
                print(f"   • tagged: [[{page.name}]] (interwiki links are invalid/redirects)")
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
    tagged_foreign_not_connected = 0
    tagged_invalid_interwiki = 0

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
            en_matches = EN_INTERWIKI_RE.findall(original_text)
            ja_matches = JA_INTERWIKI_RE.findall(original_text)
            de_matches = DE_INTERWIKI_RE.findall(original_text)
            zh_matches = ZH_INTERWIKI_RE.findall(original_text)
            ru_matches = RU_INTERWIKI_RE.findall(original_text)

            if not en_matches and not ja_matches and not de_matches and not zh_matches and not ru_matches:
                no_interwiki += 1
                continue

            # Has interwiki, try to resolve
            try:
                original = page.text()
            except:
                original = ""

            if process_page(page):
                # Check which category was added to classify the action
                try:
                    updated = page.text()
                except:
                    updated = ""

                if "{{wikidata link|" in updated and "{{wikidata link|" not in original:
                    resolved_count += 1
                elif "Foreign language page not connected to wikidata" in updated and "Foreign language page not connected to wikidata" not in original:
                    tagged_foreign_not_connected += 1
                elif "no valid interwikis" in updated and "no valid interwikis" not in original:
                    tagged_invalid_interwiki += 1

        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting
        time.sleep(0.5)

    print(f"\nDone!")
    print(f"  Resolved {resolved_count} pages with wikidata from interwiki")
    print(f"  Tagged {tagged_foreign_not_connected} pages with foreign language pages (but no wikidata)")
    print(f"  Tagged {tagged_invalid_interwiki} pages with no valid interwiki links (all redirects/missing)")
    print(f"  Skipped {no_interwiki} pages without en/ja/de/zh/ru interwikis")


if __name__ == "__main__":
    main()
