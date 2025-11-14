"""add_interwikis_from_wikidata.py
================================================
Add interwiki links from Wikidata to pages.

This script:
1. Gets all mainspace pages in [[Category:Pages linked to Wikidata]]
2. Extracts {{wikidata link|Q...}} from each page
3. Queries Wikidata for interwiki links
4. Adds interwikis to the beginning of the page with <!--interwikis from wikidata--> comment
================================================
"""

import mwclient
import requests
import re
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    # Try to find {{wikidata link|Q...}}
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Try to find [[wikidata:Q...]]
    match = re.search(r'\[\[wikidata:([Qq](\d+))\]\]', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def get_wikidata_interwikis(qid):
    """Query Wikidata for interwiki links."""
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        entity = data.get('entities', {}).get(qid, {})
        sitelinks = entity.get('sitelinks', {})

        # Extract interwiki links from sitelinks
        # Format: "de:Page Title", "en:Page Title", etc.
        interwikis = []
        for site_key, site_info in sitelinks.items():
            # Convert site key to interwiki code (e.g., "dewiki" -> "de")
            if site_key.endswith('wiki'):
                lang_code = site_key[:-4]  # Remove "wiki" suffix
                page_title = site_info.get('title', '')
                if page_title:
                    interwikis.append((lang_code, page_title))

        return interwikis

    except Exception as e:
        print(f"     ! Error querying Wikidata {qid}: {e}")
        return []


def has_interwiki_comment(page_text):
    """Check if page already has the interwiki comment."""
    return '<!--interwikis from wikidata-->' in page_text


def safe_save(page, text, summary):
    """Attempt Page.save but gracefully back off on edit-conflict."""
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


def main():
    """Add interwikis from Wikidata to all pages."""

    print("Adding interwikis from Wikidata to pages")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Pages linked to Wikidata']

    print(f"\nFetching mainspace pages in [[Category:Pages linked to Wikidata]]...")
    try:
        all_members = list(category.members())
        # Filter to mainspace only (namespace 0)
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")
    print(f"Processing pages...\n")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name

            # Get page text
            text = page.text()

            # Skip if already has interwiki comment
            if has_interwiki_comment(text):
                skipped_count += 1
                continue

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                continue

            print(f"{idx}. [[{page_name}]] ({qid})", end="")

            # Get interwikis from Wikidata
            interwikis = get_wikidata_interwikis(qid)

            if not interwikis:
                print(f" ... • No interwikis found")
                continue

            # Build interwiki string
            interwiki_lines = "<!--interwikis from wikidata-->"
            for lang_code, page_title in interwikis:
                interwiki_lines += f"[[{lang_code}:{page_title}]]"
            interwiki_lines += "\n"

            # Add to beginning of page
            new_text = interwiki_lines + text

            # Save the page
            if safe_save(page, new_text, "Bot: add interwikis from Wikidata"):
                processed_count += 1
                print(f" ... ✓ Added {len(interwikis)} interwikis")
            else:
                print(f" ... • No changes made")

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")
            error_count += 1

        # Rate limiting
        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  Skipped (already have interwikis): {skipped_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main()
