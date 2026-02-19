"""remove_en_sn_interwiki_from_templates.py
================================================
Remove [[en:...]] and [[sn:...]] interwiki links from all template pages
================================================

This script:
1. Iterates through ALL pages in the Template namespace
2. For each template page:
   - Removes all [[en:...]] interwiki links
   - Removes all [[sn:...]] interwiki links
3. One by one, inefficiently
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

# Match [[en:...]] and [[sn:...]] interwiki links
EN_SN_INTERWIKI_RE = re.compile(r'\[\[(en|sn):[^\]]+\]\]\n?', re.IGNORECASE)


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


def has_en_sn_interwiki(text):
    """Check if page has [[en:...]] or [[sn:...]] interwiki links."""
    return bool(EN_SN_INTERWIKI_RE.search(text))


def remove_en_sn_interwiki(text):
    """Remove [[en:...]] and [[sn:...]] interwiki links from text."""
    return EN_SN_INTERWIKI_RE.sub('', text)


def process_template_page(page):
    """Process a single template page."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Check if page has en/sn interwiki links
    has_interwiki = has_en_sn_interwiki(original_text)

    if has_interwiki:
        # Has en/sn interwiki - remove them
        new_text = remove_en_sn_interwiki(original_text)
        if safe_save(page, new_text, "Bot: remove [[en:...]] and [[sn:...]] interwiki links"):
            print(f"   ✓ removed en/sn interwiki links from [[{page.name}]]")
            return True

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
            if process_template_page(page):
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
