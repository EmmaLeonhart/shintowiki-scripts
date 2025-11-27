"""remove_missing_wikidata_category.py
================================================
Remove [[Category:categories missing wikidata]] from template pages
that DO have {{wikidata link|Q...}} templates.
================================================

This script:
1. Iterates through ALL pages in the Template namespace
2. For each template page:
   - Checks if it has {{wikidata link|Q...}} templates
   - If it DOES have wikidata links, removes [[Category:categories missing wikidata]]
   - If it DOES NOT have wikidata links, leaves it unchanged
3. Only removes the category, doesn't add anything
"""

import os
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
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|([Qq]\d+)}}', re.IGNORECASE)

# Match [[Category:categories missing wikidata]]
MISSING_WIKIDATA_CATEGORY_RE = re.compile(r'\[\[Category:categories missing wikidata\]\]\n?', re.IGNORECASE)


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
    """Check if page has {{wikidata link|Q...}} template."""
    return bool(WIKIDATA_TEMPLATE_RE.search(text))


def has_missing_wikidata_category(text):
    """Check if page has [[Category:categories missing wikidata]]."""
    return bool(MISSING_WIKIDATA_CATEGORY_RE.search(text))


def remove_missing_wikidata_category(text):
    """Remove [[Category:categories missing wikidata]] from text."""
    return MISSING_WIKIDATA_CATEGORY_RE.sub('', text)


def process_category_page(page):
    """Process a single category page."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check if page has wikidata link
    has_wikidata = has_wikidata_link(original_text)
    has_missing_cat = has_missing_wikidata_category(original_text)

    if has_wikidata and has_missing_cat:
        # Has wikidata but still has the "missing" category - remove it
        new_text = remove_missing_wikidata_category(original_text)
        if safe_save(page, new_text, "Bot: remove [[Category:categories missing wikidata]] (has wikidata link)"):
            print(f"   ✓ removed missing wikidata category from [[{page.name}]]")
            return True
    elif has_missing_cat and not has_wikidata:
        # Has the "missing" category and no wikidata - leave it unchanged
        print(f"   • [[{page.name}]] still missing wikidata (keeping category)")
        return False
    elif not has_missing_cat:
        # Doesn't have the category - nothing to do
        return False

    return False


def main():
    """Process all template pages."""

    print(f"Starting template namespace processing at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get all pages in Template namespace (namespace 10)
    print("Fetching all pages in Template namespace...")
    try:
        template_pages = site.allpages(namespace=10, limit=None)
    except Exception as e:
        print(f"ERROR: Could not fetch template pages – {e}")
        return

    # Convert to list to get count
    all_templates = list(template_pages)
    print(f"Found {len(all_templates)} template pages to process\n")

    modified_count = 0
    for idx, page in enumerate(all_templates, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            if process_category_page(page):
                modified_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Modified {modified_count} template pages.")


if __name__ == "__main__":
    main()
