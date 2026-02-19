#!/usr/bin/env python
"""
Verify the test pages were created correctly
"""

import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"

site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)

pages_to_check = [
    "Category:Enano Shrine",
    "Category:Ena-jinja (Takayama)",
    "Category:Kōjinja (Takayama)"
]

for page_title in pages_to_check:
    print("="*70)
    print(f"PAGE: {page_title}")
    print("="*70)
    page = site.pages[page_title]
    print(page.text())
    print()
