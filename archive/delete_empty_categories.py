#!/usr/bin/env python3
"""
Delete all empty categories (categories with zero members)
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def main():
    """Main execution."""
    print("="*70)
    print("DELETE EMPTY CATEGORIES")
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

        print("Fetching all categories...")

        # Get all pages in category namespace (namespace 14)
        all_categories = site.allpages(namespace=14)

        deleted = []
        failed = []
        non_empty = []
        category_count = 0

        for category_page in all_categories:
            category_count += 1
            print(f"Checking {category_count}: {category_page.name}...", end=" ", flush=True)

            try:
                # Get category members
                members = list(category_page.members())
                member_count = len(members)

                if member_count == 0:
                    # Category is empty, delete it
                    print(f"[EMPTY - DELETING]", flush=True)
                    try:
                        category_page.delete("Deleting empty category")
                        deleted.append(category_page.name)
                    except Exception as e:
                        print(f"  ✗ Delete failed: {e}", flush=True)
                        failed.append((category_page.name, str(e)))
                else:
                    print(f"[HAS {member_count} MEMBERS - KEEPING]", flush=True)
                    non_empty.append((category_page.name, member_count))

                # Rate limit
                time.sleep(1.5)

            except Exception as e:
                print(f"[ERROR - {e}]", flush=True)
                failed.append((category_page.name, str(e)))
                continue

        # Summary
        print(f"\n{'='*70}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Total categories checked: {category_count}")
        print(f"Deleted (empty): {len(deleted)}")
        print(f"Kept (non-empty): {len(non_empty)}")
        print(f"Failed: {len(failed)}")
        print()

        if deleted:
            print("DELETED CATEGORIES:")
            for cat_name in deleted[:30]:  # Show first 30
                print(f"  {cat_name}")
            if len(deleted) > 30:
                print(f"  ... and {len(deleted) - 30} more")
            print()

        if failed:
            print("FAILED CATEGORIES:")
            for cat_name, reason in failed[:10]:  # Show first 10
                print(f"  {cat_name}: {reason}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
