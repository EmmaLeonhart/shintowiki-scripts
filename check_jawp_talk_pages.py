#!/usr/bin/env python3
"""
Check Japanese Wikipedia pages in specific categories for talk page discussions
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to Japanese Wikipedia
print("Connecting to Japanese Wikipedia...", flush=True)
site = mwclient.Site('ja.wikipedia.org', clients_useragent='ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)')

categories_to_check = [
    'Category:式内社の一覧',
    'Category:式内社関連テンプレート'
]

print(f"\nChecking {len(categories_to_check)} categories for talk pages...\n")
print("=" * 80)

all_pages_with_talk = []
all_pages_without_talk = []

for cat_name in categories_to_check:
    print(f"\n{cat_name}")
    print("-" * 80)

    try:
        print(f"  Accessing category page...", flush=True)
        category = site.pages[cat_name]

        print(f"  Fetching category members...", flush=True)
        pages = []
        for i, page in enumerate(category.members(), 1):
            pages.append(page)
            if i % 10 == 0:
                print(f"  Fetched {i} pages...", flush=True)

        print(f"Found {len(pages)} pages in this category\n")

        for page in pages:
            # Skip category and file pages, focus on articles and templates
            if page.namespace in [0, 10]:  # Main namespace and Template namespace
                # Determine talk page name based on namespace
                if page.namespace == 0:
                    talk_page_name = f"Talk:{page.name}"
                elif page.namespace == 10:
                    talk_page_name = f"Template talk:{page.name}"

                talk_page = site.pages[talk_page_name]

                if talk_page.exists:
                    talk_text = talk_page.text()
                    if talk_text and talk_text.strip():
                        print(f"✓ {page.name}")
                        print(f"  → Talk page: {talk_page_name}")
                        print(f"  → Length: {len(talk_text)} characters")
                        # Show first 200 characters of talk page
                        preview = talk_text[:200].replace('\n', ' ')
                        print(f"  → Preview: {preview}...")
                        print()
                        all_pages_with_talk.append((cat_name, page.name, talk_page_name, len(talk_text)))
                    else:
                        all_pages_without_talk.append((cat_name, page.name, "empty"))
                else:
                    all_pages_without_talk.append((cat_name, page.name, "doesn't exist"))

                # Rate limiting - wait 2 seconds between each page check
                time.sleep(2)

    except Exception as e:
        print(f"Error processing {cat_name}: {e}")
        continue

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nPages WITH talk page discussions: {len(all_pages_with_talk)}")
if all_pages_with_talk:
    print("\nDetailed list:")
    for cat, page, talk, length in all_pages_with_talk:
        print(f"  • {page}")
        print(f"    Category: {cat}")
        print(f"    Talk page: {talk} ({length} chars)")
        print()

print(f"\nPages WITHOUT talk pages: {len(all_pages_without_talk)}")
if all_pages_without_talk and len(all_pages_without_talk) <= 20:
    print("\nList:")
    for cat, page, status in all_pages_without_talk:
        print(f"  • {page} ({status})")

print("\nDone!")
