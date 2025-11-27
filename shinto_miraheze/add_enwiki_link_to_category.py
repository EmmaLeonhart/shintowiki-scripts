"""add_enwiki_link_to_category.py
================================================
Add [[en:{{subst:FULLPAGENAME}}]] to all pages in a category.
================================================

This script:
1. Fetches all pages in [[Category:enwiki overwritten pages]]
2. For each page, appends [[en:{{subst:FULLPAGENAME}}]] to the end
3. Saves the modified page with an appropriate summary
"""

import os
import time
import mwclient
import sys
import re

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
CATEGORY  = 'enwiki overwritten pages'  # Without "Category:" prefix

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")


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


def has_enwiki_fullpage_link(text):
    """Check if page already has [[en:{{subst:FULLPAGENAME}}]] link."""
    return bool(re.search(r'\[\[en:\{\{subst:FULLPAGENAME\}\}\]\]', text))


def add_enwiki_link(text):
    """Add [[en:{{subst:FULLPAGENAME}}]] to the end of the page."""
    # Check if already present
    if has_enwiki_fullpage_link(text):
        return text  # Already has the FULLPAGENAME link

    # Strip trailing whitespace and add the link
    text = text.rstrip()
    text += "\n[[en:{{subst:FULLPAGENAME}}]]"

    return text


def process_page(page):
    """Add enwiki link to a page."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check if already has the FULLPAGENAME link
    if has_enwiki_fullpage_link(original_text):
        print(f"   • [[{page.name}]] already has [[en:{{{{subst:FULLPAGENAME}}}}]] link")
        return False

    # Add the link
    new_text = add_enwiki_link(original_text)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, "Bot: add [[en:{{subst:FULLPAGENAME}}]]"):
            print(f"   • added enwiki FULLPAGENAME link to [[{page.name}]]")
            return True

    return False


def main():
    """Fetch all pages in the category and add the enwiki link."""

    print(f"Fetching pages from [[Category:{CATEGORY}]]...\n")

    try:
        # Get the category page
        category = site.pages[f'Category:{CATEGORY}']
        pages = list(category)
    except Exception as e:
        print(f"ERROR: Could not fetch category – {e}")
        return

    if not pages:
        print(f"No pages found in [[Category:{CATEGORY}]]")
        return

    print(f"Found {len(pages)} pages to process\n")

    modified_count = 0
    for idx, page in enumerate(pages, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            if process_page(page):
                modified_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Modified {modified_count} pages.")


if __name__ == "__main__":
    main()
