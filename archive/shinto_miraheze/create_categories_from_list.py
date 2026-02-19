#!/usr/bin/env python3
"""
create_categories_from_list.py
==============================
Creates a category page for every title found in **pages.txt** with the
single line:
    [[Category:Tier 0 Categories]]

• If the category already exists, it does **not** overwrite existing text;
  it just appends the tag if missing.
• Requires mwclient and write permission on the local wiki.
"""
import os, sys, time, urllib.parse
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_2]"
PAGES_TXT = "pages.txt"; THROTTLE = 0.4
TIER0_TAG = "[[Category:Tier 0 Categories]]"

# ─── UTILS ─────────────────────────────────────────────────────────

def load_titles():
    if not os.path.exists(PAGES_TXT):
        print("Missing pages.txt"); sys.exit(1)
    with open(PAGES_TXT, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

def normalise(title:str)->str:
    """Strip leading Category: and convert underscores to spaces."""
    if title.lower().startswith("category:"):
        title = title[9:]
    return urllib.parse.unquote(title).replace('_',' ')

# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    for idx, raw in enumerate(load_titles(), 1):
        cat_name = normalise(raw)
        full = f"Category:{cat_name}"
        pg = site.pages[full]
        print(f"{idx}. {full}")
        if pg.exists and not pg.redirect:
            txt = pg.text()
            if TIER0_TAG in txt:
                print("   • already has Tier‑0 tag; skipped")
            else:
                try:
                    pg.save(txt.rstrip() + "\n" + TIER0_TAG + "\n",
                             summary="Bot: add Tier 0 tag")
                    print("   ✓ tag appended")
                except APIError as e:
                    print("   ! failed to save:", e.code)
        else:
            body = TIER0_TAG + "\n"
            try:
                pg.save(body, summary="Bot: create Tier 0 category")
                print("   ✓ category created")
            except APIError as e:
                print("   ! create failed:", e.code)
        time.sleep(THROTTLE)

    print("Done.")

if __name__ == '__main__':
    main()
