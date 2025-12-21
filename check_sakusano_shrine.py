#!/usr/bin/env python
"""
Check the full content of Category:Sakusano Shrine
"""

import mwclient

COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"

site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
page = site.pages["Category:Sakusano Shrine"]

print("Full content of Category:Sakusano Shrine:")
print("="*70)
print(page.text())
print("="*70)
