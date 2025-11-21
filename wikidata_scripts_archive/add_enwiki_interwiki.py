"""add_enwiki_interwiki.py
================================================
Add English Wikipedia interwiki links from Wikidata.
================================================

This script:
1. Reads pages from pages.txt
2. Extracts QID from {{wikidata link|Q...}} template or [[d:Q...]] in text
3. Queries Wikidata to find English Wikipedia article
4. Adds [[en:Title]] if found and not already present
5. Adds [[Category:pages with a usurping enwiki page]]

Only modifies pages that have a Wikidata QID and an enwiki link on Wikidata.
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
# Match {{wikidata link|Q...}}
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|([Qq](\d+))}}')

# Match [[d:Q...]]
WIKIDATA_LINK_RE = re.compile(r'\[\[d:([Qq]\d+)\]\]')

# Match existing [[en:...]] interwiki
EN_INTERWIKI_RE = re.compile(r'\[\[en:[^\]]+\]\]')

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


def extract_qid(text):
    """Extract QID from {{wikidata link|Q...}} or [[d:Q...]], preferring template."""
    # Try template first
    match = WIKIDATA_TEMPLATE_RE.search(text)
    if match:
        return match.group(1).upper()

    # Fall back to [[d:Q...]]
    match = WIKIDATA_LINK_RE.search(text)
    if match:
        return match.group(1).upper()

    return None


def get_enwiki_title_from_wikidata(qid):
    """Query Wikidata API to find English Wikipedia article title for a QID."""
    try:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "format": "json"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Navigate to the entity
        if "entities" not in data:
            return None

        entity = data["entities"].get(qid, {})
        if "sitelinks" not in entity:
            return None

        sitelinks = entity["sitelinks"]

        # Look for English Wikipedia
        if "enwiki" in sitelinks:
            return sitelinks["enwiki"]["title"]

        return None
    except Exception as e:
        return None


def has_en_interwiki(text):
    """Check if page already has [[en:...]] interwiki."""
    return bool(EN_INTERWIKI_RE.search(text))


def add_enwiki_interwiki_and_category(text, enwiki_title):
    """Add [[en:Title]] interwiki and category to the page."""
    # Remove any existing wikidata link templates to re-add later
    text_without_wikidata = WIKIDATA_TEMPLATE_RE.sub('', text)

    # Extract existing categories
    categories = CATEGORY_RE.findall(text_without_wikidata)
    text_without_cats = CATEGORY_RE.sub('', text_without_wikidata)

    # Build new content
    content = text_without_cats.rstrip()

    # Add en interwiki if not present
    en_link = f"[[en:{enwiki_title}]]"
    if not has_en_interwiki(content):
        content += f"\n{en_link}"

    # Ensure category list
    if categories:
        content += "\n\n"
        # Add the new category and existing ones
        new_category = "[[Category:pages with a usurping enwiki page]]"
        if new_category not in categories:
            categories.insert(0, new_category)
        # Deduplicate
        categories = list(dict.fromkeys(categories))
        content += "\n".join(f"[[Category:{cat}]]" for cat in categories)
    else:
        content += "\n\n[[Category:pages with a usurping enwiki page]]"

    content += "\n"

    return content


def process_page(page):
    """Process a single page to add English interwiki."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Extract QID
    qid = extract_qid(original_text)
    if not qid:
        # No wikidata reference found
        return False

    # Query Wikidata for English Wikipedia article
    enwiki_title = get_enwiki_title_from_wikidata(qid)
    if not enwiki_title:
        # No English Wikipedia article on Wikidata
        return False

    # Check if already has en interwiki
    if has_en_interwiki(original_text):
        print(f"   • [[{page.name}]] already has en: interwiki")
        return False

    # Add the interwiki and category
    new_text = add_enwiki_interwiki_and_category(original_text, enwiki_title)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: add en: interwiki from Wikidata ({qid})"):
            print(f"   • added en: interwiki [[en:{enwiki_title}]] to [[{page.name}]] (from {qid})")
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
