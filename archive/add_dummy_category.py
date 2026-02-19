#!/usr/bin/env python3
"""
add_dummy_category.py
=====================
Adds [[Category:pages]] to the end of every page in mainspace and category namespace.
This is to fix category population after wiki restoration.
"""

import mwclient
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.5  # seconds between edits (increased to avoid rate limiting)

CATEGORY_TO_ADD = "[[Category:pages]]"
EDIT_SUMMARY = "adding dummy category to make categories work"

# For category namespace, start from this page
CAT_NS_START_FROM = "City districts"
# For mainspace, only process pages in this category
MAINSPACE_CATEGORY = "Wikidata generated shikinaisha pages"

def main():
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    total_processed = 0
    total_success = 0
    total_failed = 0
    total_skipped = 0

    # Process both namespaces: 0 (mainspace) and 14 (category)
    namespaces = [0, 14]
    namespace_names = {0: "Mainspace", 14: "Category"}

    for ns in namespaces:
        print(f"\n{'='*60}")
        print(f"Processing {namespace_names[ns]} (namespace {ns})")
        print('='*60)

        # Get pages based on namespace
        if ns == 0:
            # Mainspace: only process pages in the specified category
            print(f"Getting pages from [[Category:{MAINSPACE_CATEGORY}]]...")
            pages = site.categories[MAINSPACE_CATEGORY]
        elif ns == 14:
            # Category namespace: start from CAT_NS_START_FROM
            pages = site.allpages(namespace=ns, start=CAT_NS_START_FROM)
            print(f"[RESUME] Starting from {CAT_NS_START_FROM}")
        else:
            pages = site.allpages(namespace=ns)

        for page in pages:
            total_processed += 1
            page_title = page.name

            try:
                # Get current content
                content = page.text()

                # Check if category already exists
                if CATEGORY_TO_ADD in content or "[[Category:pages]]" in content.lower():
                    print(f"[SKIP] {page_title} (already has category)")
                    total_skipped += 1
                    continue

                # Add the category at the end
                new_content = content.rstrip() + "\n" + CATEGORY_TO_ADD

                # Save the page
                page.save(new_content, summary=EDIT_SUMMARY)
                print(f"[OK] {page_title}")
                total_success += 1

            except Exception as e:
                print(f"[FAILED] {page_title}: {e}")
                total_failed += 1

            time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print('='*60)
    print(f"Total processed: {total_processed}")
    print(f"Successfully edited: {total_success}")
    print(f"Skipped (already has category): {total_skipped}")
    print(f"Failed: {total_failed}")

if __name__ == "__main__":
    main()
