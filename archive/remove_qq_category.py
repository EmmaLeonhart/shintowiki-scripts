#!/usr/bin/env python3
"""
Remove all pages from [[Category:qq]]
"""

import sys
import io
import re
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
    print("REMOVE PAGES FROM [[Category:qq]]")
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
        category_name = "qq"
        print(f"Retrieving pages from [[Category:{category_name}]]...")

        category = site.pages[f'Category:{category_name}']
        pages = list(category.members())

        print(f"Found {len(pages)} pages in category\n")

        modified = []
        failed = []
        page_count = 0

        for page in pages:
            page_count += 1
            print(f"Processing {page_count}/{len(pages)}: {page.name}...", end=" ", flush=True)

            try:
                page_text = page.text()

                # Remove [[Category:qq]] (case insensitive)
                new_text = re.sub(r'\[\[Category:qq\]\]\n?', '', page_text, flags=re.IGNORECASE)

                if new_text != page_text:
                    # Changes were made
                    page.save(new_text, summary="Removing from [[Category:qq]]")
                    print(f"[MODIFIED]", flush=True)
                    modified.append(page.name)
                else:
                    print(f"[NO CHANGES]", flush=True)

                # Rate limit
                time.sleep(1.5)

            except Exception as e:
                print(f"[ERROR - {e}]", flush=True)
                failed.append((page.name, str(e)))
                continue

        # Summary
        print(f"\n{'='*70}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Modified: {len(modified)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {page_count}")
        print()

        if modified:
            print("MODIFIED PAGES:")
            for page_name in modified[:20]:  # Show first 20
                print(f"  {page_name}")
            if len(modified) > 20:
                print(f"  ... and {len(modified) - 20} more")
            print()

        if failed:
            print("FAILED PAGES:")
            for page_name, reason in failed[:10]:  # Show first 10
                print(f"  {page_name}: {reason}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
