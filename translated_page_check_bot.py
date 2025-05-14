#!/usr/bin/env python3
"""
translated_page_check_bot.py
============================
Sweep main-namespace pages on shinto.miraheze.org and:

- Log and skip redirects.
- If a page has NO {{translated page|…}} → append [[Category:Pages without translation templates]].
- Else, within that single template invocation replace any numbered params (1=,2=,3=,…) with qq=,
  but leave version= and comment= intact.

Usage:
  python translated_page_check_bot.py
"""

import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
PAGES_FILE = ''     # optional: list of pages to process. If missing or empty, sweep all ns=0.
THROTTLE   = 0.5             # seconds between edits

# ─── LOGIN ────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME!r}")

# ─── REGEXES ───────────────────────────────────────────────────────
# detect presence of the template
TRANSLATED_RE = re.compile(r'\{\{\s*translated\s+page\|', re.IGNORECASE)
# capture the entire translated-page template invocation (non-greedy)
TRANSLATED_TPL_RE = re.compile(r'(\{\{\s*translated\s+page\|.*?\}\})',
                               re.IGNORECASE | re.DOTALL)
# within that snippet, find numeric params to rewrite
NUMBERED_PARAM_RE = re.compile(r'\|\s*\d+\s*=')

# ─── HELPERS ───────────────────────────────────────────────────────
def load_pages():
    try:
        with open(PAGES_FILE, encoding='utf-8') as fh:
            lines = [l.strip() for l in fh if l.strip() and not l.startswith('#')]
            return lines
    except FileNotFoundError:
        return []

def safe_save(page, new_text, summary):
    """Save only if text changed, handle conflicts gracefully."""
    try:
        old = page.text()
    except Exception as e:
        print(f"   ! could not fetch [[{page.name}]] text: {e}")
        return False
    if old.strip() == new_text.strip():
        return False
    try:
        page.save(new_text, summary=summary)
        return True
    except APIError as e:
        if e.code == 'editconflict':
            print(f"   ! edit conflict on [[{page.name}]] – skipped")
            return False
        print(f"   ! APIError on [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"   ! error saving [[{page.name}]]: {e}")
    return False

# ─── PROCESS ONE PAGE ──────────────────────────────────────────────
def process_page(page):
    if page.redirect:
        print(f"   ↳ [[{page.name}]] is a redirect; skipped")
        return

    text = page.text()
    if not TRANSLATED_RE.search(text):
        # no translated-page template at all
        if '[[Category:Pages without translation templates]]' not in text:
            new = text.rstrip() + "\n\n[[Category:Pages without translation templates]]\n"
            if safe_save(page, new,
                         "Bot: mark page as missing translated-page template"):
                print(f"   • [[{page.name}]] → added missing-template category")
    else:
        # fix numbered params only inside the one template invocation
        def fix_tpl(m):
            tpl = m.group(1)
            fixed = NUMBERED_PARAM_RE.sub('|qq=', tpl)
            return fixed

        new_text = TRANSLATED_TPL_RE.sub(fix_tpl, text)
        if new_text != text:
            if safe_save(page, new_text,
                         "Bot: normalize numbered params to qq= in translated-page"):
                print(f"   • [[{page.name}]] → rewrote numeric params → qq=")

# ─── MAIN LOOP ────────────────────────────────────────────────────
def main():
    pages = load_pages()
    if pages:
        targets = pages
        total = len(pages)
    else:
        targets = (p.name for p in site.allpages(namespace=0, start="tl "))
        total = "all mainspace"
    print(f"Processing {total} pages…")
    for idx, title in enumerate(targets, start=1):
        print(f"{idx}/{total}: [[{title}]]", end="")
        page = site.pages[title]
        try:
            process_page(page)
        except Exception as e:
            print(f"\n   ! unexpected error on [[{title}]]: {e}")
        time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()
