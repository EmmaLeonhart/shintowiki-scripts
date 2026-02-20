#!/usr/bin/env python3
"""
Fetch full content of the 3 talk pages found
"""

import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to Japanese Wikipedia
print("Connecting to Japanese Wikipedia...", flush=True)
site = mwclient.Site('ja.wikipedia.org',
                     clients_useragent='ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)')

talk_pages = [
    'Talk:出雲国の式内社一覧',
    'Talk:丹後国の式内社一覧',
    'Talk:対馬島の式内社一覧'
]

print("\n" + "=" * 80)
print("FULL TALK PAGE CONTENT")
print("=" * 80)

for talk_page_name in talk_pages:
    print(f"\n{'=' * 80}")
    print(f"{talk_page_name}")
    print("=" * 80)

    try:
        page = site.pages[talk_page_name]
        if page.exists:
            text = page.text()
            print(text)
            print()
        else:
            print("(Page does not exist)")
    except Exception as e:
        print(f"Error fetching page: {e}")

print("\n" + "=" * 80)
print("END OF TALK PAGES")
print("=" * 80)
