"""tag_missing_wikidata_all_pages.py
================================================
Tag all pages without wikidata links (excluding redirects).
================================================

This script:
1. Reads a list of page titles from a file
2. For each page that is NOT a redirect and lacks {{wikidata link|...}}
3. Adds [[Category:Missing wikidata]] to the page

This helps identify which pages need wikidata links added.
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
PASSWORD  = '[REDACTED_SECRET_2]'
PAGES_FILE = 'C:\\Users\\Immanuelle\\Downloads\\VijmYVCm.txt'
MISSING_WIKIDATA_CATEGORY = 'Missing wikidata'

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

# Match redirect syntax
REDIRECT_RE = re.compile(r'^\s*#REDIRECT\s*\[\[', re.IGNORECASE)

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


def is_redirect(text):
    """Check if page is a redirect."""
    return bool(REDIRECT_RE.match(text))


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

    # Check if it's a redirect - skip if so
    if is_redirect(original_text):
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


def main():
    """Read pages file and process each page."""

    try:
        with open(PAGES_FILE, 'r', encoding='utf-8') as f:
            titles = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"ERROR: Could not read {PAGES_FILE} – {e}")
        return

    if not titles:
        print(f"ERROR: No pages found in {PAGES_FILE}")
        return

    print(f"Processing {len(titles)} pages...\n")

    tagged_count = 0
    redirects_skipped = 0
    already_has_wikidata = 0

    for idx, title in enumerate(titles, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")

            # Quick check for redirects and wikidata
            try:
                text = page.text()
                if is_redirect(text):
                    redirects_skipped += 1
                elif has_wikidata_link(text):
                    already_has_wikidata += 1
                elif process_page(page):
                    tagged_count += 1
            except Exception as e:
                print(f"   ! error checking page – {e}")

        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone!")
    print(f"  Tagged {tagged_count} pages as missing wikidata")
    print(f"  Skipped {redirects_skipped} redirects")
    print(f"  Skipped {already_has_wikidata} pages that already have wikidata")


if __name__ == "__main__":
    main()
