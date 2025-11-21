"""add_wikidata_from_id_interwiki.py
================================================
Add wikidata link templates from Indonesian Wikipedia interwiki links.
================================================

This script:
1. Reads pages from pages.txt
2. Finds [[id:...]] interwiki links on the page
3. For each Indonesian Wikipedia article found, queries Wikidata for the QID
4. Adds {{wikidata link|QID}} template to the bottom of the page

Only modifies pages that have Indonesian interwiki links that exist on Wikidata.
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
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
PAGES_TXT = 'pages.txt'

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
# Match [[id:...]] interwiki links
ID_INTERWIKI_RE = re.compile(r'\[\[id:([^\]]+)\]\]')

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


def extract_id_interwiki(text):
    """Extract Indonesian Wikipedia article title from [[id:...]]."""
    match = ID_INTERWIKI_RE.search(text)
    if match:
        return match.group(1)
    return None


def get_qid_from_wikipedia(wiki_title, language="id"):
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
        response = requests.get(url, params=params, timeout=10)
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
    """Process a single page to add wikidata link from Indonesian interwiki."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Extract Indonesian interwiki link
    id_article = extract_id_interwiki(original_text)
    if not id_article:
        # No Indonesian interwiki found
        return False

    # Query Wikidata for the QID
    qid = get_qid_from_wikipedia(id_article, "id")
    if not qid:
        # No Wikidata entry found for this Indonesian Wikipedia article
        print(f"   • [[{page.name}]] has [[id:{id_article}]] but no Wikidata entry found")
        return False

    # Check if this QID already exists in the page
    existing_qids = extract_existing_qids(original_text)
    qid_upper = qid.upper()
    if qid_upper in existing_qids:
        print(f"   • [[{page.name}]] already has {{{{wikidata link|{qid_upper}}}}}")
        return False

    # Add the template
    new_text = add_wikidata_template_to_bottom(original_text, qid_upper)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: add wikidata link from Indonesian interwiki ({qid_upper})"):
            print(f"   • added {{{{wikidata link|{qid_upper}}}}} to [[{page.name}]] from [[id:{id_article}]]")
            return True

    return False


def main():
    """Read pages.txt and process each page."""

    if not os.path.exists(PAGES_TXT):
        print(f"ERROR: {PAGES_TXT} not found!")
        return

    with open(PAGES_TXT, 'r', encoding='utf-8') as f:
        titles = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(titles)} pages from {PAGES_TXT}...\n")

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
