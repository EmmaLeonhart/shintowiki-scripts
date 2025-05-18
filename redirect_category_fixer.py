#!/usr/bin/env python3
"""
redirect_category_fixer.py
==========================

Reads **redirect_categories.txt** (one category title per line) and for each
category that is a *redirect* to another local category, moves every page in
the redirect category to the *target* category.

How it works
------------
1. Normalises each line (strip `Category:` prefix, convert `_` → space).
2. Checks whether `Category:<name>` exists and is a redirect to
   `Category:<target>`.
3. Queries the member pages of the *redirect* category (non‑redirect pages).
4. On every member page, replaces
       `[[Category:Old]]` or `[[Category:Old|…]]`
   with   `[[Category:Target]]` / `[[Category:Target|…]]`
   (`Old`/`Target` are space‑normalised). Saves each page with summary
   “Bot: move category Old → Target”.
5. Does **not** delete the redirect category itself (keeps it as redirect).

Requirements: `mwclient`, write rights.
"""
import os, re, time, urllib.parse, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL    = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME    = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
CAT_FILE    = "redirect_categories.txt"
THROTTLE    = 0.5

REDIR_RX = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)", re.I)

# ─── UTILS ─────────────────────────────────────────────────────────

def norm(title: str) -> str:
    if title.lower().startswith("category:"):
        title = title[9:]
    return urllib.parse.unquote(title).replace('_', ' ').strip()


def load_cat_list():
    if not os.path.exists(CAT_FILE):
        raise SystemExit("Missing redirect_categories.txt")
    with open(CAT_FILE, encoding="utf-8") as fh:
        return [norm(l) for l in fh if l.strip() and not l.startswith('#')]


def member_pages(site, cat_full):
    cm = site.api(action='query', list='categorymembers', cmtitle=cat_full,
                  cmtype='page', cmlimit='max', format='json')
    return [m['title'] for m in cm['query']['categorymembers']]


def swap_cat_on_page(page, old, new):
    txt = page.text()
    old_rx = re.escape(old).replace(r"\ ", "[ _]")  # space or underscore
    pat = re.compile(rf"\[\[\s*Category:{old_rx}([^\]]*)\]\]", re.I)
    if not pat.search(txt):
        return False
    new_txt = pat.sub(lambda m: f"[[Category:{new}{m.group(1)}]]", txt)
    if new_txt == txt:
        return False
    try:
        page.save(new_txt, summary=f"Bot: move category {old} → {new}")
        print("    • updated", page.name)
        return True
    except APIError as e:
        print("    ! failed", page.name, e.code)
        return False

# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    for cat in load_cat_list():
        full = f"Category:{cat}"
        pg = site.pages[full]
        print("→", full)
        if not pg.exists or not pg.redirect:
            print("  • not a redirect – skipped")
            continue
        m = REDIR_RX.match(pg.text())
        if not m:
            print("  • cannot parse redirect target – skipped")
            continue
        target = urllib.parse.unquote(m.group(1)).replace('_',' ').strip()
        print(f"  • target: {target}")
        for title in member_pages(site, full):
            swap_cat_on_page(site.pages[title], cat, target)
            time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()
