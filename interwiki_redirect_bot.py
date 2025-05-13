#!/usr/bin/env python3
"""
interwiki_redirect_bot.py
=========================
For every page title listed in pages.txt, overwrite the page
with a redirect to the same title on English Wikipedia:

    #redirect [[en:{{subst:PAGENAME}}]]

Configure credentials and pages.txt, then run:
    python interwiki_redirect_bot.py
"""

import os
import sys
import time

import mwclient
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
PAGES_FILE = 'pages.txt'
THROTTLE   = 0.5   # seconds between edits
SUMMARY    = 'Bot: convert to interwiki redirect to English'

# ─── HELPERS ────────────────────────────────────────────────────────
def load_pages(path):
    if not os.path.exists(path):
        print(f"Error: {path!r} not found.")
        sys.exit(1)
    titles = []
    with open(path, encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if ln and not ln.startswith('#'):
                titles.append(ln)
    if not titles:
        print(f"No pages listed in {path}; nothing to do.")
        sys.exit(0)
    return titles

# ─── LOGIN ─────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME!r}")

# ─── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    titles = load_pages(PAGES_FILE)
    total = len(titles)
    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{total}: [[{title}]] → ", end='', flush=True)
        page = site.pages[title]
        redirect_text = "#redirect [[en:{{subst:PAGENAME}}]]\n"
        try:
            page.save(redirect_text, summary=SUMMARY)
            print("redirected")
        except APIError as e:
            print(f"APIError({e.code}); skipped")
        except Exception as e:
            print(f"Error({e}); skipped")
        time.sleep(THROTTLE)
    print("All done.")

if __name__ == '__main__':
    main()
