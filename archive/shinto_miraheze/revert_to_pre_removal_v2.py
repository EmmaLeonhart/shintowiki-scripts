#!/usr/bin/env python3
"""
Revert pages to pre-removal state using direct HTTP API requests.
For each page, find the most recent revision whose summary does NOT start with "Remove"
and restore that version's content.
"""

import sys
import io
import time
import requests
import mwclient
from urllib.parse import urljoin

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki configuration
WIKI_URL = 'https://shinto.miraheze.org'
WIKI_API = urljoin(WIKI_URL, '/w/api.php')
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def main():
    """Main execution."""
    print("="*70)
    print("REVERT PAGES TO PRE-REMOVAL STATE (v2 - Direct HTTP API)")
    print("="*70)
    print()

    try:
        # Login to wiki with mwclient
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site('shinto.miraheze.org', path='/w/')
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        # Get all pages in category
        category_name = "Wikidata generated shikinaisha pages"
        print(f"Retrieving pages from [[Category:{category_name}]]...")

        reverted = []
        failed = []
        skipped = []
        page_count = 0

        # Get auth token from mwclient's session
        session = requests.Session()
        session.headers.update({'User-Agent': 'Immanuelle_wikibot/1.0'})

        # Copy cookies from mwclient to requests session
        if hasattr(site.connection, 'cookies'):
            session.cookies.update(site.connection.cookies)

        # Ensure we have CSRF token for edits later
        csrf_token_response = session.get(WIKI_API, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'}, timeout=10)
        csrf_token_response.raise_for_status()
        csrf_token = csrf_token_response.json()['query']['tokens']['csrftoken']

        # Iterate through category members
        try:
            for page in site.api('query', list='categorymembers', cmtitle=f'Category:{category_name}', cmlimit='max')['query']['categorymembers']:
                page_title = page['title']
                page_ns = page['ns']

                # Only process mainspace pages (ns=0)
                if page_ns != 0:
                    continue

                page_count += 1
                print(f"Processing {page_count}: {page_title}...", end=" ", flush=True)

                try:
                    # Get revision history using direct API
                    rv_data = {
                        'action': 'query',
                        'titles': page_title,
                        'prop': 'revisions',
                        'rvlimit': 50,
                        'rvprop': 'timestamp|user|comment|content',
                        'format': 'json'
                    }

                    response = session.get(WIKI_API, params=rv_data, timeout=10)
                    response.raise_for_status()
                    result = response.json()

                    pages = result.get('query', {}).get('pages', {})
                    if not pages:
                        print("[NO PAGE DATA]")
                        skipped.append(page_title)
                        continue

                    page_data = list(pages.values())[0]
                    revisions = page_data.get('revisions', [])

                    if not revisions:
                        print("[NO REVISIONS]")
                        skipped.append(page_title)
                        continue

                    # Find the most recent revision whose comment does NOT start with "Remove"
                    target_revision = None
                    target_text = None
                    for rev in revisions:
                        comment = rev.get('comment', '')
                        if not comment.startswith('Remove'):
                            target_revision = rev
                            target_text = rev.get('*', '')
                            break

                    if not target_revision:
                        print("[NO PRE-REMOVAL REVISION]")
                        skipped.append(page_title)
                        continue

                    # Get current page text via mwclient
                    page_obj = site.pages[page_title]
                    current_text = page_obj.text()

                    if current_text == target_text:
                        print("[ALREADY REVERTED]")
                        skipped.append(page_title)
                    else:
                        # Revert to target version using mwclient (already authenticated)
                        page_obj.edit(target_text, summary="Revert to pre-removal state")
                        print("[REVERTED]")
                        reverted.append(page_title)

                    # Rate limit
                    time.sleep(1.5)

                except Exception as e:
                    print(f"[ERROR - {e}]")
                    failed.append((page_title, str(e)))
                    continue

        except Exception as e:
            print(f"Error retrieving category members: {e}")
            import traceback
            traceback.print_exc()

        # Summary
        print(f"\n{'='*70}")
        print(f"REVERSION SUMMARY")
        print(f"{'='*70}")
        print(f"Reverted: {len(reverted)}")
        print(f"Skipped: {len(skipped)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {page_count}")
        print()

        if reverted:
            print("REVERTED PAGES:")
            for page in reverted[:20]:  # Show first 20
                print(f"  {page}")
            if len(reverted) > 20:
                print(f"  ... and {len(reverted) - 20} more")
            print()

        if failed:
            print("FAILED PAGES:")
            for page, reason in failed[:10]:  # Show first 10
                print(f"  {page}: {reason}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
