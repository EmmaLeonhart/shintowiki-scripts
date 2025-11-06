"""clean_enwiki_interwiki.py
================================================
Remove invalid English Wikipedia interwiki links.
================================================

This script:
1. Reads a list of page titles from a file
2. For each page, finds [[en:...]] interwiki links
3. Checks if those pages actually exist on English Wikipedia
4. Removes interwiki links that point to non-existent pages

This cleans up erroneous enwiki interwiki links.
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
# Match [[en:...]] interwiki links
EN_INTERWIKI_RE = re.compile(r'\[\[en:([^\]]+)\]\]')

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


def page_exists_on_enwiki(page_title):
    """Check if a page exists on English Wikipedia."""
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": page_title,
            "format": "json"
        }
        headers = {
            "User-Agent": "Shinto Wiki Bot (https://shinto.miraheze.org/)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "query" not in data or "pages" not in data["query"]:
            return False

        pages = data["query"]["pages"]
        if not pages:
            return False

        # Get the first (and should be only) page
        page = next(iter(pages.values()))

        # Check if page exists (no "missing" key means it exists)
        return "missing" not in page
    except Exception as e:
        print(f"      ! error checking enwiki – {e}")
        return False


def extract_en_interwikis(text):
    """Extract all English Wikipedia article titles from [[en:...]]."""
    matches = EN_INTERWIKI_RE.findall(text)
    return matches


def process_page(page):
    """Process a single page to remove invalid enwiki interwiki links."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Find all en: interwiki links
    en_links = extract_en_interwikis(original_text)
    if not en_links:
        # No English interwiki found
        return False

    # Check each link and mark invalid ones for removal
    invalid_links = []
    for en_title in en_links:
        if not page_exists_on_enwiki(en_title):
            invalid_links.append(en_title)

    if not invalid_links:
        # All links are valid
        return False

    # Remove the invalid links
    new_text = original_text
    for en_title in invalid_links:
        # Escape special regex characters in the title
        escaped_title = re.escape(en_title)
        pattern = r'\[\[en:' + escaped_title + r'\]\]'
        new_text = re.sub(pattern, '', new_text)

    # Clean up any double newlines created by removal
    new_text = re.sub(r'\n\n\n+', '\n\n', new_text)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, f"Bot: remove invalid enwiki interwiki links"):
            count = len(invalid_links)
            link_word = "link" if count == 1 else "links"
            removed = ", ".join(f"[[en:{t}]]" for t in invalid_links)
            print(f"   • removed {count} invalid enwiki {link_word}: {removed}")
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

    cleaned_count = 0
    pages_checked = 0

    for idx, title in enumerate(titles, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")

            try:
                if process_page(page):
                    cleaned_count += 1
                pages_checked += 1
            except Exception as e:
                print(f"   ! error processing page – {e}")

        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone!")
    print(f"  Cleaned {cleaned_count} pages by removing invalid enwiki interwiki links")
    print(f"  Checked {pages_checked} pages")


if __name__ == "__main__":
    main()
