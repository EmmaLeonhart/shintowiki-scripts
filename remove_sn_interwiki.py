"""remove_sn_interwiki.py
================================================
Remove Shona (sn:) interwiki links from pages.
================================================

This script:
1. Reads a list of page titles from a file
2. For each page, finds and removes [[sn:...]] interwiki links
3. Saves the modified pages

Shona interwiki links are often incorrect on this wiki, so this removes them.
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
PAGES_FILE = 'C:\\Users\\Immanuelle\\Downloads\\VijmYVCm.txt'

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
# Match [[sn:...]] interwiki links (with newlines accounted for)
SN_INTERWIKI_RE = re.compile(r'\[\[sn:[^\]]+\]\]')

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


def process_page(page):
    """Process a single page to remove Shona interwiki links."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Find all sn: interwiki links
    sn_links = SN_INTERWIKI_RE.findall(original_text)
    if not sn_links:
        # No Shona interwiki found
        return False

    # Remove the links
    new_text = SN_INTERWIKI_RE.sub('', original_text)

    # Clean up any double newlines created by removal
    new_text = re.sub(r'\n\n\n+', '\n\n', new_text)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: remove incorrect Shona (sn:) interwiki links"):
            count = len(sn_links)
            link_word = "link" if count == 1 else "links"
            print(f"   • removed {count} Shona interwiki {link_word} from [[{page.name}]]")
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

    print(f"\nDone! Cleaned {modified_count} pages by removing Shona interwiki links.")


if __name__ == "__main__":
    main()
