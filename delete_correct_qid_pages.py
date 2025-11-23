#!/usr/bin/env python3
"""
delete_correct_qid_pages.py
===========================
Delete all the correct QID pages listed
"""

import mwclient
import sys
import time

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

print("Logged in\n")

# List of pages to delete
pages_to_delete = [
    'Futsuno Shrine (Q135039005)',
    'Hafuritano Shrine (Q135039044)',
    'Hatano Shrine (Q135039019)',
    'Hatorino Shrine (Q135098838)',
    'Honoikatsuchino Shrine (Q135038947)',
    'Izanagi Shrine (Q11379365)',
    'Kahamatano Shrine (Q135039016)',
    'Kakitano Shrine (Q135039192)',
    'Kamo Shrine (Q135039165)',
    'Kamono Shrine (Q135098878)',
    'Kamusakino Shrine (Q135039190)',
    'Kataoka Shrine (Q43594918)',
    'Kawamata Shrine (Q11553360)',
    'Kineno Shrine (Q135039225)',
    'Kinpu Shrine (Q3197197)',
    'Kuhiwokano Shrine (Q135038802)',
    'Murayano Shrine (Q135098841)',
    'Nagata Shrine (Q661395)',
    'Nifuno Shrine (Q135038979)',
    'Nomano Shrine (Q135039228)',
    'Nomi Shrine (Q11646130)',
    'Ohokurano Shrine (Q135038788)',
    'Ohotsuno Shrine (Q135039122)',
    'Okamino Shrine (Q135039195)',
    'Sai Shrine (Q135098830)',
    'Sakahino Shrine (Q135039131)',
    'Sakatono Shrine (Q135039031)',
    'Takase Shrine (Q11671973)',
]

print(f"Will delete {len(pages_to_delete)} pages\n")

# Delete each page
successful = 0
failed = 0

for i, page_title in enumerate(pages_to_delete, 1):
    print(f"{i}. Deleting [[{page_title}]]...")

    try:
        page = site.Pages[page_title]
        page.delete("Delete correct QID page (no longer needed)")

        print(f"   ✓ Deleted\n")
        successful += 1

    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        failed += 1

    time.sleep(1.5)

print(f"\n=== Summary ===")
print(f"Successfully deleted: {successful}/{len(pages_to_delete)}")
print(f"Failed: {failed}/{len(pages_to_delete)}")
