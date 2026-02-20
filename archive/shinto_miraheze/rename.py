#!/usr/bin/env python3
"""
move_pages_to_5_bot.py
======================
For every page listed in pages.txt:
 1. Move → Title-5 (no redirect)
"""

import os
import sys
import time

import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL    = "shinto.miraheze.org"
WIKI_PATH   = "/w/"
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_2]"
PAGES_FILE  = "pages.txt"
THROTTLE    = 1.0     # seconds between moves

# ─── LOGIN ─────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")

# ─── HELPERS ───────────────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh
                if ln.strip() and not ln.startswith("#")]

def move_page(title):
    page = site.pages[title]
    if not page.exists:
        print(f"  ! [[{title}]] does not exist, skipping")
        return

    new_title = f"{title}-5"
    try:
        page.move(new_title, reason="Bot: batch move to -5", no_redirect=True)
        print(f"  • Moved [[{title}]] → [[{new_title}]]")
    except APIError as e:
        print(f"  ! Move failed for [[{title}]]: {e.code}")

# ─── MAIN LOOP ───────────────────────────────────────────────────────
def main():
    titles = load_titles(PAGES_FILE)
    total = len(titles)
    for idx, title in enumerate(titles, 1):
        print(f"\n{idx}/{total}: Processing [[{title}]]")
        move_page(title)
        time.sleep(THROTTLE)
    print("\nAll done.")

if __name__ == "__main__":
    main()
