#!/usr/bin/env python3
"""
Delete all members of [[Category:Year type categories that appear not to exist]]
from evolutionism.miraheze.org
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def main():
    """Main execution."""
    print("="*70)
    print("DELETE YEAR TYPE CATEGORIES THAT APPEAR NOT TO EXIST")
    print("="*70)
    print()

    try:
        # Login to wiki
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        # Get all pages in category
        category_name = "Year type categories that appear not to exist"
        print(f"Retrieving members of [[Category:{category_name}]]...")

        deleted = []
        failed = []
        page_count = 0

        # Iterate through category members
        try:
            for page in site.api('query', list='categorymembers', cmtitle=f'Category:{category_name}', cmlimit='max')['query']['categorymembers']:
                page_title = page['title']
                page_ns = page['ns']

                page_count += 1
                print(f"{page_count}: Deleting '{page_title}'...", end=" ", flush=True)

                try:
                    page_obj = site.pages[page_title]

                    # Delete the page
                    page_obj.delete(reason="Deleting non-existent year type category")
                    print("[DELETED]")
                    deleted.append(page_title)

                    # Rate limit
                    time.sleep(1.5)

                except Exception as e:
                    print(f"[FAILED] {str(e)[:50]}")
                    failed.append((page_title, str(e)))
                    time.sleep(1.5)
                    continue

        except Exception as e:
            print(f"Error retrieving category members: {e}")
            import traceback
            traceback.print_exc()

        # Summary
        print("\n" + "="*70)
        print(f"DELETION SUMMARY")
        print("="*70)
        print(f"Deleted: {len(deleted)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {page_count}")
        print()

        if deleted:
            print("DELETED PAGES:")
            for page in deleted[:20]:
                print(f"  {page}")
            if len(deleted) > 20:
                print(f"  ... and {len(deleted) - 20} more")
            print()

        if failed:
            print("FAILED DELETIONS:")
            for page, reason in failed[:10]:
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
