"""tag_missing_wikidata_category.py
================================================
Tag Islamic Calendar Days pages without wikidata links.
================================================

This script:
1. Gets all pages from [[Category:Islamic Calendar Days]]
2. Checks if each page has a {{wikidata link|...}} template
3. If not, adds [[Category:Islamic Calendar Days without wikidata]] to the page

Only processes pages without wikidata links.
"""

import time
import re
import mwclient
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
MISSING_WIKIDATA_CATEGORY = 'Islamic Calendar Days without wikidata'

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
# Match existing {{wikidata link|Q...}} templates
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|[Qq]\d+}}')

# Match the missing wikidata category
MISSING_CATEGORY_RE = re.compile(r'\[\[Category:' + re.escape(MISSING_WIKIDATA_CATEGORY) + r'\]\]')

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


def has_wikidata_link(text):
    """Check if page has any {{wikidata link|...}} templates."""
    return bool(WIKIDATA_TEMPLATE_RE.search(text))


def already_has_missing_category(text):
    """Check if page already has the missing wikidata category."""
    return bool(MISSING_CATEGORY_RE.search(text))


def add_missing_wikidata_category(text):
    """Add the missing wikidata category to the page."""
    # Ensure text ends properly
    text = text.rstrip()

    # Add the category
    text += f"\n[[Category:{MISSING_WIKIDATA_CATEGORY}]]\n"

    return text


def process_page(page):
    """Process a single page to tag it if it's missing wikidata."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check if page has wikidata link
    if has_wikidata_link(original_text):
        # Page has wikidata link, skip it
        return False

    # Check if already tagged
    if already_has_missing_category(original_text):
        # Already tagged, skip
        return False

    # Add the missing wikidata category
    new_text = add_missing_wikidata_category(original_text)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, "Bot: tag pages missing wikidata links"):
            print(f"   • tagged [[{page.name}]] as missing wikidata")
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

    tagged_count = 0
    for idx, title in enumerate(titles, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")
            if process_page(page):
                tagged_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Tagged {tagged_count} pages as missing wikidata.")


if __name__ == "__main__":
    main()
