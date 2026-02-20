#!/usr/bin/env python3
"""
fix_double_redirects.py
=======================
Reads page titles from pages.txt and for each page:

  - If it’s not a redirect → do nothing.
  - If it redirects to itself or into a loop → delete the page.
  - If it redirects to another redirect → change it to point
    directly to the final (non-redirect) target.

Redirect targets that can’t be fetched (invalid titles, interwiki, etc.)
are treated as final.  Errors are caught and logged; the run continues.

Requires bot credentials with delete and edit rights.
"""

import os
import re
import sys
import time

import mwclient
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_2]'
PAGES_FILE = 'pages.txt'
THROTTLE   = 0.5   # seconds between operations

DEL_SUMMARY   = 'Bot: remove self-redirect'
REDIR_SUMMARY = 'Bot: fix double redirect to final target'

# capture "#redirect [[Target]]", case-insensitive, allow whitespace
REDIR_RE = re.compile(r'(?mi)^\s*#\s*redirect\s*\[\[\s*([^\]\|]+)', re.IGNORECASE)

def load_titles(path):
    if not os.path.exists(path):
        print(f"Error: {path!r} not found.")
        sys.exit(1)
    with open(path, encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

def parse_redirect_target(text):
    m = REDIR_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()

def safe_save(page, new_text, summary):
    try:
        current = page.text()
    except Exception as e:
        print(f"    ! fetch error on [[{page.name}]]: {e}")
        return False
    if current.strip() == new_text.strip():
        return False
    try:
        page.save(new_text, summary=summary)
        return True
    except APIError as e:
        if e.code == 'editconflict':
            print(f"    ! edit conflict on [[{page.name}]]; skipped")
            return False
        print(f"    ! APIError saving [[{page.name}]]: {e.code}")
        return False
    except Exception as e:
        print(f"    ! save error on [[{page.name}]]: {e}")
        return False

def main():
    # login
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME!r}")

    titles = load_titles(PAGES_FILE)
    total = len(titles)

    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{total}: [[{title}]]", end='')
        page = site.pages[title]
        try:
            text = page.text()
        except Exception as e:
            print(f" → ! could not fetch text: {e}")
            continue

        target = parse_redirect_target(text)
        if not target:
            print(" → (not a redirect)")
            time.sleep(THROTTLE)
            continue

        # resolve chain
        seen = {title}
        final = target
        looped = False
        while True:
            if final in seen:
                looped = True
                break
            seen.add(final)

            # try to fetch the next page
            try:
                tgt_page = site.pages[final]
                tgt_text = tgt_page.text()
            except Exception:
                # can’t fetch, assume this is final
                break

            nxt = parse_redirect_target(tgt_text)
            if not nxt:
                # reached a non-redirect
                break
            final = nxt

        # handle self-redirects / loops
        if looped or final == title:
            try:
                page.delete(reason=DEL_SUMMARY, watch=False)
                print(" → deleted self/loop redirect")
            except APIError as e:
                print(f" → ! delete failed: {e.code}")
            except Exception as e:
                print(f" → ! delete error: {e}")
        elif final != target:
            # fix to point directly to final
            new_text = f"#REDIRECT [[{final}]]\n"
            if safe_save(page, new_text, REDIR_SUMMARY):
                print(f" → fixed → [[{final}]]")
            else:
                print(" → no change needed")
        else:
            print(" → redirect OK")

        time.sleep(THROTTLE)

    print("Done.")

if __name__ == '__main__':
    main()
