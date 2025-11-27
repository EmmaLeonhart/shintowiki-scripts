#!/usr/bin/env python3
"""finalize_ashitaka_shrine.py
================================================
Wait 2 hours, then fetch Ashitaka Shrine from specific revision and remove from category
================================================

This script:
1. Waits 2 hours to allow all version updates to complete
2. Fetches content from revision oldid=5079605
3. Copies that content to the current page
4. Removes [[Category:Wikidata generated shikinaisha pages]] from the page
5. Edits the page with the finalized content
"""

import mwclient
import requests
import sys
import time
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

WAIT_TIME = 2 * 60 * 60  # 2 hours in seconds
PAGE_NAME = 'Ashitaka Shrine'
REVISION_ID = '5079605'
CATEGORY_TO_REMOVE = '[[Category:Wikidata generated shikinaisha pages]]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def get_revision_content(page_name, revision_id):
    """Fetch content from a specific revision using MediaWiki API."""
    try:
        params = {
            'action': 'query',
            'titles': page_name,
            'revids': revision_id,
            'prop': 'revisions',
            'rvprop': 'content',
            'format': 'json'
        }

        url = f'https://{WIKI_URL}{WIKI_PATH}api.php'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Navigate the response structure
        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            revisions = page_data.get('revisions', [])
            if revisions:
                return revisions[0].get('*')

        return None
    except Exception as e:
        print(f"Error fetching revision {revision_id}: {e}")
        return None


def remove_category(content, category):
    """Remove a category from page content."""
    # Remove the category line (with or without whitespace)
    pattern = r'\n?' + re.escape(category) + r'\n?'
    modified_content = re.sub(pattern, '', content)
    return modified_content


def format_hours_minutes(seconds):
    """Format seconds as hours and minutes."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def main():
    """Main function - wait then finalize Ashitaka Shrine."""

    print("="*70)
    print("ASHITAKA SHRINE FINALIZATION SCRIPT")
    print("="*70)
    print(f"\nThis script will:")
    print(f"  1. Wait {format_hours_minutes(WAIT_TIME)} for all updates to complete")
    print(f"  2. Fetch content from revision {REVISION_ID}")
    print(f"  3. Remove the Wikidata category")
    print(f"  4. Save the finalized page")
    print(f"\nStarting wait at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Will execute at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + WAIT_TIME))}")
    print("\n" + "="*70 + "\n")

    # Wait 2 hours
    print(f"Waiting {format_hours_minutes(WAIT_TIME)} for updates to complete...")

    start_time = time.time()
    check_interval = 300  # Check every 5 minutes

    while time.time() - start_time < WAIT_TIME:
        elapsed = time.time() - start_time
        remaining = WAIT_TIME - elapsed

        # Print progress every 5 minutes
        if int(elapsed) % check_interval == 0:
            print(f"  [{format_hours_minutes(elapsed)} elapsed] {format_hours_minutes(remaining)} remaining...")

        time.sleep(1)

    print(f"\n✓ Wait period complete!")
    print(f"\nProceeding to finalize {PAGE_NAME}...\n")

    # Fetch the revision content
    print(f"1. Fetching content from revision {REVISION_ID}...")
    revision_content = get_revision_content(PAGE_NAME, REVISION_ID)

    if not revision_content:
        print(f"   ! ERROR: Could not fetch revision {REVISION_ID}")
        return

    print(f"   ✓ Retrieved {len(revision_content)} characters from revision")

    # Remove the category
    print(f"\n2. Removing category '{CATEGORY_TO_REMOVE}'...")
    finalized_content = remove_category(revision_content, CATEGORY_TO_REMOVE)

    if finalized_content == revision_content:
        print(f"   ! WARNING: Category not found in revision content")
    else:
        print(f"   ✓ Category removed (saved {len(revision_content) - len(finalized_content)} characters)")

    # Get the page and save
    print(f"\n3. Saving finalized content to {PAGE_NAME}...")
    try:
        page = site.pages[PAGE_NAME]
        page.edit(
            finalized_content,
            summary="Bot: Finalize Ashitaka Shrine - use revision content and remove Wikidata generation category"
        )
        print(f"   ✓ Page saved successfully!")
    except mwclient.errors.EditConflict:
        print(f"   ! ERROR: Edit conflict occurred")
        return
    except Exception as e:
        print(f"   ! ERROR: {e}")
        return

    print(f"\n" + "="*70)
    print(f"✓ FINALIZATION COMPLETE")
    print(f"="*70)
    print(f"\nPage: {PAGE_NAME}")
    print(f"Revision used: {REVISION_ID}")
    print(f"Category removed: {CATEGORY_TO_REMOVE}")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
