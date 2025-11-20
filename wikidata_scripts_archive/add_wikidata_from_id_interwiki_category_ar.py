"""add_wikidata_from_id_interwiki_category_ar.py
================================================
Add wikidata link templates from Arabic Wikipedia interwiki links.
Reads pages from a specific category instead of pages.txt.
================================================

This script:
1. Gets all pages from [[Category:Islamic Calendar Days]]
2. Finds [[ar:...]] interwiki links on each page
3. For each Arabic Wikipedia article found, queries Wikidata for the QID
4. Adds {{wikidata link|QID}} template to the bottom of the page

Only modifies pages that have Arabic interwiki links that exist on Wikidata.
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
CATEGORY_NAME = 'Islamic Calendar Days'

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
# Match [[ar:...]] interwiki links
AR_INTERWIKI_RE = re.compile(r'\[\[ar:([^\]]+)\]\]')

# Match existing {{wikidata link|Q...}} templates
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|([Qq](\d+))}}')

# Match category links
CATEGORY_RE = re.compile(r'\[\[Category:[^\]]+\]\]')

# ─── HELPERS ─────────────────────────────────────────────────

def safe_save(page, text, summary):
    """Attempt Page.save but gracefully back off on edit-conflict or if
    the page vanished (was deleted) before we got to save."""
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


def extract_ar_interwiki(text):
    """Extract Arabic Wikipedia article title from [[ar:...]]."""
    match = AR_INTERWIKI_RE.search(text)
    if match:
        return match.group(1)
    return None


def get_qid_from_wikipedia(wiki_title, language="ar"):
    """Query Wikidata to find QID for a Wikipedia article."""
    try:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "sites": f"{language}wiki",
            "titles": wiki_title,
            "props": "info",
            "format": "json"
        }
        headers = {
            "User-Agent": "Shinto Wiki Bot (https://shinto.miraheze.org/)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Get the first (and should be only) entity
        if "entities" not in data:
            return None

        entities = data["entities"]
        if not entities:
            return None

        # Get the first entity (will have numeric or "-1" key)
        entity = next(iter(entities.values()))

        # Check if it's a valid entity (not a failed lookup)
        if "missing" in entity:
            return None

        if "id" in entity:
            return entity["id"]

        return None
    except Exception as e:
        return None


def extract_existing_qids(text):
    """Extract all existing QIDs from {{wikidata link|Q...}} templates."""
    matches = WIKIDATA_TEMPLATE_RE.findall(text)
    qids = set()
    for match in matches:
        qids.add(match[0].upper())
    return qids


def add_wikidata_template_to_bottom(text, qid):
    """Add {{wikidata link|QID}} to the bottom of the page."""
    # Remove any existing wikidata link templates
    text = WIKIDATA_TEMPLATE_RE.sub('', text)

    # Ensure text ends properly
    text = text.rstrip()

    # Add the template
    text += f"\n{{{{wikidata link|{qid}}}}}\n"

    return text


def process_page(page):
    """Process a single page to add wikidata link from Arabic interwiki."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check if page already has ANY wikidata links
    existing_qids = extract_existing_qids(original_text)
    if existing_qids:
        # Page already has wikidata links, skip it
        return False

    # Extract Arabic interwiki link
    ar_article = extract_ar_interwiki(original_text)
    if not ar_article:
        # No Arabic interwiki found
        return False

    # Query Wikidata for the QID
    qid = get_qid_from_wikipedia(ar_article, "ar")
    if not qid:
        # No Wikidata entry found for this Arabic Wikipedia article
        print(f"   • [[{page.name}]] has [[ar:{ar_article}]] but no Wikidata entry found")
        return False

    # At this point we know: no existing wikidata links, has Arabic interwiki, and QID found
    qid_upper = qid.upper()

    # Add the template
    new_text = add_wikidata_template_to_bottom(original_text, qid_upper)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: add wikidata link from Arabic interwiki ({qid_upper})"):
            print(f"   • added {{{{wikidata link|{qid_upper}}}}} to [[{page.name}]] from [[ar:{ar_article}]]")
            return True

    return False


def get_category_pages(category_name):
    """Get all pages in a category using the API."""
    try:
        titles = []
        cmcontinue = None

        while True:
            params = {
                'action': 'query',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category_name}',
                'cmlimit': 500,
                'cmtype': 'page',  # Only get pages, not subcategories
                'format': 'json'
            }

            if cmcontinue:
                params['cmcontinue'] = cmcontinue

            response = site.api(**params)

            if 'query' in response and 'categorymembers' in response['query']:
                for member in response['query']['categorymembers']:
                    titles.append(member['title'])

            # Check for continuation
            if 'continue' in response:
                cmcontinue = response['continue'].get('cmcontinue')
            else:
                break

        return titles
    except Exception as e:
        print(f"ERROR: Could not fetch pages from category – {e}")
        return []


def main():
    """Get pages from category and process each page."""

    print(f"Fetching pages from Category:{CATEGORY_NAME}...\n")
    titles = get_category_pages(CATEGORY_NAME)

    if not titles:
        print(f"ERROR: No pages found in Category:{CATEGORY_NAME}")
        return

    print(f"Found {len(titles)} pages. Processing...\n")

    modified_count = 0
    for idx, title in enumerate(titles, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")
            if process_page(page):
                modified_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Modified {modified_count} pages.")


if __name__ == "__main__":
    main()
