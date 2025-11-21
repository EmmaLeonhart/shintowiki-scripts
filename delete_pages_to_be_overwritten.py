"""delete_pages_to_be_overwritten.py
================================================
Delete all pages in [[Category:Pages to be overwritten]]
================================================

This script:
1. Fetches all pages in [[Category:Pages to be overwritten]]
2. Deletes each one
3. Processes one by one, inefficiently
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

def delete_page(page):
    """Delete a page."""
    try:
        if not page.exists:
            print(f"   • page already deleted")
            return False

        page.delete(reason="Bot: delete page marked for overwriting")
        return True
    except mwclient.errors.APIError as e:
        if e.code == "cantdelete":
            print(f"   ! cannot delete page (protected or other reason)")
            return False
        raise
    except Exception as e:
        print(f"   ! delete failed: {e}")
        return False


def main():
    """Process all pages in the category."""

    print(f"Starting deletion at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get the category
    category = site.pages['Category:Pages to be overwritten']

    print(f"Fetching all pages in [[Category:Pages to be overwritten]]...")
    try:
        members = list(category.members())
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} pages to delete\n")

    deleted_count = 0
    for idx, page in enumerate(members, 1):
        try:
            print(f"{idx}. [[{page.name}]]")

            if delete_page(page):
                deleted_count += 1
                print(f"   ✓ deleted successfully")

        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Deleted {deleted_count} pages.")


if __name__ == "__main__":
    main()
