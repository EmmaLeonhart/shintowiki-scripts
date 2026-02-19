"""replace_overwrite_category.py
================================================
Replace all pages in [[Category:Pages_to_be_overwritten]] with redirect stubs.
================================================

This script:
1. Fetches all pages in the Pages_to_be_overwritten category
2. For each page, replaces the entire content with:
   #redirect[[{{subst:FULLPAGENAME}}]]
   [[Category:Automatic wikipedia redirects starting with FIRST_LETTER]]
   where FIRST_LETTER is the first character of the page name

Example: "1 solar year" becomes:
   #redirect[[{{subst:FULLPAGENAME}}]]
   [[Category:Automatic wikipedia redirects starting with 1]]
"""

import os
import time
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
CATEGORY  = 'Pages to be overwritten'  # Without "Category:" prefix

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


def get_first_letter(page_name):
    """Get the first character of the page name for the category suffix."""
    if not page_name:
        return "?"
    return page_name[0]


def create_redirect_stub(page_name):
    """Create a redirect stub with the appropriate category."""
    first_letter = get_first_letter(page_name)
    redirect = (
        "#redirect[[{{subst:FULLPAGENAME}}]]\n"
        f"[[Category:Automatic wikipedia redirects starting with {first_letter}]]\n"
    )
    return redirect


def process_page(page):
    """Replace page content with redirect stub."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Create the redirect stub
    new_text = create_redirect_stub(page.name)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, "Bot: replace with redirect stub"):
            print(f"   • replaced [[{page.name}]] with redirect (letter: {get_first_letter(page.name)})")
            return True
    else:
        print(f"   • [[{page.name}]] already has correct redirect stub")
        return False

    return False


def main():
    """Fetch all pages in the category and replace them."""

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

    for idx, page in enumerate(pages, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            process_page(page)
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print("\nDone!")


if __name__ == "__main__":
    main()
