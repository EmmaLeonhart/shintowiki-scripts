"""delete_unused_redirects.py
================================================
Delete redirects with no incoming links in mainspace, category, and template namespaces
================================================

This script:
1. Iterates through mainspace (0), category (14), and template (10) namespaces
2. For each redirect page:
   - Checks if it has any incoming links
   - If NO incoming links, deletes it
   - If it has incoming links, leaves it unchanged
3. Processes one by one, inefficiently
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


# ─── HELPERS ─────────────────────────────────────────────────

def is_redirect(page):
    """Check if a page is a redirect."""
    try:
        text = page.text()
        return text.strip().lower().startswith('#redirect')
    except Exception:
        return False


def has_incoming_links(page_title, namespace):
    """Check if a page has incoming links using the API."""
    try:
        # Query for backlinks to this page
        result = site.api(
            'query',
            list='backlinks',
            bltitle=page_title,
            blnamespace='0|10|14',  # Only check mainspace, template, category
            bllimit=1  # Just need to know if there's at least one
        )

        backlinks = result.get('query', {}).get('backlinks', [])
        return len(backlinks) > 0
    except Exception as e:
        print(f"      ! Error checking backlinks for {page_title}: {e}")
        return True  # Assume it has links if we can't check (safer)


def delete_page(page, reason):
    """Delete a page."""
    try:
        if not page.exists:
            print(f"      • page already deleted")
            return False

        page.delete(reason=reason)
        return True
    except mwclient.errors.APIError as e:
        if e.code == "cantdelete":
            print(f"      ! cannot delete page (protected or other reason)")
            return False
        raise
    except Exception as e:
        print(f"      ! delete failed: {e}")
        return False


def process_namespace(namespace_id, namespace_name):
    """Process all redirects in a given namespace."""

    print(f"\n{'='*60}")
    print(f"Processing {namespace_name} namespace (ID: {namespace_id})")
    print(f"{'='*60}\n")

    print(f"Fetching all pages in {namespace_name}...")
    try:
        all_pages = site.allpages(namespace=namespace_id, limit=None)
    except Exception as e:
        print(f"ERROR: Could not fetch pages – {e}")
        return 0

    all_pages_list = list(all_pages)
    print(f"Found {len(all_pages_list)} pages to check\n")

    deleted_count = 0
    for idx, page in enumerate(all_pages_list, 1):
        try:
            page_name = page.name
            print(f"{idx}. [[{page_name}]]")

            # Check if it's a redirect
            if not is_redirect(page):
                print(f"   • not a redirect")
                continue

            print(f"   - is redirect, checking for incoming links...")

            # Check for incoming links
            if has_incoming_links(page_name, namespace_id):
                print(f"   • has incoming links (keeping)")
                continue

            # No incoming links - delete it
            print(f"   ✓ no incoming links, deleting...")
            if delete_page(page, f"Bot: delete unused redirect (no incoming links)"):
                deleted_count += 1
                print(f"   ✓ deleted successfully")

        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\n{namespace_name}: Deleted {deleted_count} unused redirects.")
    return deleted_count


def main():
    """Process all namespaces."""

    print(f"\nStarting unused redirect deletion at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    total_deleted = 0

    # Process mainspace (0)
    total_deleted += process_namespace(0, "Mainspace")

    # Process category (14)
    total_deleted += process_namespace(14, "Category")

    # Process template (10)
    total_deleted += process_namespace(10, "Template")

    print(f"\n{'='*60}")
    print(f"TOTAL: Deleted {total_deleted} unused redirects")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
