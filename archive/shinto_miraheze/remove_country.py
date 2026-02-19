#!/usr/bin/env python3
"""
Remove all country (P17) section headings from pages in
[[Category:Wikidata generated shikinaisha pages]]
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
    print("REMOVE COUNTRY (P17) HEADINGS")
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
        category_name = "Wikidata generated shikinaisha pages"
        print(f"Retrieving pages from [[Category:{category_name}]]...")

        modified = []
        failed = []
        page_count = 0

        # Iterate through category members
        try:
            for page in site.api('query', list='categorymembers', cmtitle=f'Category:{category_name}', cmlimit='max')['query']['categorymembers']:
                page_title = page['title']
                page_ns = page['ns']

                # Only process mainspace pages (ns=0)
                if page_ns != 0:
                    continue

                page_count += 1
                print(f"Processing {page_count}: {page_title}...", end=" ")

                try:
                    page_obj = site.pages[page_title]
                    page_text = page_obj.text()

                    # Look for P17 heading and its content - remove until next heading or end
                    pattern = r'==\s*country \(P17\)\s*==\s*\n(?:(?!==)[\s\S])*'

                    new_text = re.sub(pattern, '', page_text)

                    if new_text != page_text:
                        # Changes were made
                        page_obj.edit(new_text, summary="Remove country (P17) section heading")
                        print(f"[MODIFIED]")
                        modified.append(page_title)
                    else:
                        print(f"[NO CHANGES]")

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
        print(f"PROCESSING SUMMARY")
        print(f"{'='*70}")
        print(f"Modified: {len(modified)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {page_count}")
        print()

        if modified:
            print("MODIFIED PAGES:")
            for page in modified[:20]:  # Show first 20
                print(f"  {page}")
            if len(modified) > 20:
                print(f"  ... and {len(modified) - 20} more")
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
