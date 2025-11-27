"""add_wikidata_links.py
================================================
Adds wikidata link templates to Shinto wiki pages.
================================================

This script:
1. Scans all pages in pages.txt for [[d:Q...]] references
2. Extracts the QID from each reference
3. Deduplicates QIDs on the same page
4. Appends {{wikidata link|QXXXX}} to the bottom of each page

If multiple different QIDs are found on a page, adds multiple templates.
If multiple references to the same QID exist, adds only one template.
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
# Match [[d:Q...]] format
WIKIDATA_LINK_RE = re.compile(r'\[\[d:([Qq]\d+)\]\]')

# Match existing wikidata link templates at the bottom
EXISTING_WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|[Qq]\d+}}')

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


def extract_qids(text):
    """Extract all QIDs from [[d:Q...]] references and return deduplicated list."""
    matches = WIKIDATA_LINK_RE.findall(text)
    # Normalize to uppercase and deduplicate while preserving order
    seen = set()
    qids = []
    for qid in matches:
        qid_upper = qid.upper()
        if qid_upper not in seen:
            seen.add(qid_upper)
            qids.append(qid_upper)
    return qids


def add_wikidata_templates(text, qids):
    """Append wikidata link templates to the bottom of the page.

    Returns the modified text.
    """
    if not qids:
        return text

    # Remove any existing wikidata link templates
    text = EXISTING_WIKIDATA_TEMPLATE_RE.sub('', text)

    # Ensure text ends properly
    text = text.rstrip()

    # Add the templates
    for qid in qids:
        text += f"\n{{{{wikidata link|{qid}}}}}"

    text += '\n'
    return text


def process_page(page):
    """Process a single page to add wikidata link templates."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return

    # Extract QIDs from [[d:Q...]] references
    qids = extract_qids(original_text)

    if not qids:
        # No wikidata references found
        return

    # Add templates to the bottom
    new_text = add_wikidata_templates(original_text, qids)

    # Save if changed
    if new_text != original_text:
        if safe_save(page, new_text, "Bot: add wikidata link templates"):
            print(f"   • added {len(qids)} wikidata link(s) to [[{page.name}]]: {', '.join(qids)}")
    else:
        print(f"   • [[{page.name}]] already has wikidata templates")


def main():
    """Read pages.txt and process each page."""

    if not os.path.exists(PAGES_TXT):
        print(f"ERROR: {PAGES_TXT} not found!")
        return

    with open(PAGES_TXT, 'r', encoding='utf-8') as f:
        titles = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(titles)} pages from {PAGES_TXT}...\n")

    for idx, title in enumerate(titles, 1):
        try:
            page = site.pages[title]
            print(f"{idx}. [[{title}]]")
            process_page(page)
        except Exception as e:
            try:
                print(f"{idx}. [[{title}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print("\nDone!")


if __name__ == "__main__":
    main()
