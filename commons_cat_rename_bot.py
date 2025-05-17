#!/usr/bin/env python3
"""
commons_cat_rename_bot.py  (overwrite-redirect, preserve text)
=============================================================

For each canonical category listed in pages.txt:

  * page must still contain [[Category:Categories created from dewiki title]]
  * page must contain exactly ONE [[commons:Category:...]] wikilink

Steps
-----
1. If Category:<CommonsName> already exists **and is a redirect**, delete it.
   If it exists and is NOT a redirect → skip (safety).
2. Move Category:<JapaneseName> → Category:<CommonsName>
   (MediaWiki will leave a redirect at the JP title).
3. On the moved page:
     – remove the dewiki-creation tag line
     – append [[Category:wikimedia commons named categories]] if absent
4. On every page that still uses the old JP category *or* any other
   redirect pointing to the Commons category, change the link to the
   Commons name.
"""

import os, re, sys, time, urllib.parse
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL   = "shinto.miraheze.org"
SITE_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_TXT  = "pages.txt"

TAG_JA   = "Categories created from dewiki title"
TAG_COMM = "wikimedia commons named categories from de"
THROTTLE = 0.5  # seconds between edits/saves

# ─── SESSION ────────────────────────────────────────────────────────
site = mwclient.Site(SITE_URL, path=SITE_PATH)
site.login(USERNAME, PASSWORD)

# ─── REGEXES ────────────────────────────────────────────────────────
RE_COMMONS = re.compile(r"\[\[\s*commons\s*:\s*Category\s*:([^\]|]+)", re.I)
RE_TAG_JA  = re.compile(rf"\s*\[\[\s*Category:{re.escape(TAG_JA)}\s*\]\]\s*\n?",
                        re.I)

# ─── HELPERS ────────────────────────────────────────────────────────
def load_titles():
    if not os.path.exists(PAGES_TXT):
        print("Create pages.txt first.")
        sys.exit(1)
    with open(PAGES_TXT, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def redirect_titles_to(target_full):
    params = {"action":"query","list":"backlinks","bltitle":target_full,
              "blfilterredir":"redirects","bllimit":"max","format":"json"}
    while True:
        data = site.api(**params)
        for bl in data["query"]["backlinks"]:
            yield bl["title"]
        if "continue" not in data:
            break
        params.update(data["continue"])

def pages_in_category(cat_name):
    for cm in site.api("query", list="categorymembers", cmtitle=f"Category:{cat_name}",
                       cmlimit="max")["query"]["categorymembers"]:
        yield cm["title"]

def replace_cat(title, old_cat, new_cat):
    p   = site.pages[title]
    txt = p.text()
    pattern = re.compile(rf"\[\[\s*Category:{re.escape(old_cat)}([^\]]*)\]\]",
                         re.I)
    if not pattern.search(txt):
        return
    new = pattern.sub(f"[[Category:{new_cat}\\1]]", txt)
    if new == txt:
        return
    try:
        p.save(new, summary=f"Bot: update category → {new_cat}")
        print(f"        • fixed [[{title}]]")
    except APIError as e:
        print(f"        ! save failed [[{title}]]: {e.code}")

# ─── CORE ───────────────────────────────────────────────────────────
def process(canon_cat):
    canon_full = f"Category:{canon_cat}"
    page       = site.pages[canon_full]
    if not page.exists:
        print("  ! canonical category missing – skipped")
        return

    text = page.text()
    if TAG_JA.lower() not in text.lower():
        print("  • no dewiki-creation tag – skipped")
        return

    commons_links = list(dict.fromkeys(RE_COMMONS.findall(text)))
    if len(commons_links) != 1:
        print("  • zero / multiple commons links – skipped")
        return
    commons_cat = urllib.parse.unquote(commons_links[0]).replace("_", " ")
    if commons_cat == canon_cat:
        print("  • already matches Commons name – nothing to do")
        return
    commons_full = f"Category:{commons_cat}"
    target_page  = site.pages[commons_full]

    # -- if target exists and is redirect, delete it ----------------
    if target_page.exists:
        if not target_page.redirect:
            print("  ! target exists & not a redirect – skipped")
            return
        try:
            target_page.delete(reason="Bot: overwrite with proper category", watch=False)
            print("    • deleted existing redirect at target")
        except APIError as e:
            print(f"  ! cannot delete redirect at target: {e.code}")
            return

    # -- move --------------------------------------------------------
    try:
        page.move(commons_full, reason="Bot: rename to Commons category")
        print(f"    ✓ moved to [[{commons_full}]]")
    except APIError as e:
        print(f"  ! move failed: {e.code}")
        return

    # -- update tags on new page ------------------------------------
    moved_page = site.pages[commons_full]
    moved_txt  = moved_page.text()
    moved_txt  = RE_TAG_JA.sub("", moved_txt)
    if f"[[Category:{TAG_COMM}]]" not in moved_txt:
        moved_txt = moved_txt.rstrip() + f"\n[[Category:{TAG_COMM}]]\n"
    try:
        moved_page.save(moved_txt, summary="Bot: mark as Commons-named category")
    except APIError as e:
        print(f"  ! updating tag failed: {e.code}")

    # -- fix links in original JP category members ------------------
    for member in pages_in_category(canon_cat):
        replace_cat(member, canon_cat, commons_cat)

    # -- fix links in members of other redirects --------------------
    for red_title in redirect_titles_to(commons_full):
        red_cat = red_title.split(":", 1)[1]
        if red_cat.lower() == commons_cat.lower():
            continue
        print(f"    ↳ extra redirect {red_cat}")
        for m in pages_in_category(red_cat):
            replace_cat(m, red_cat, commons_cat)

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    cats = load_titles()
    for idx, cat in enumerate(cats, 1):
        print(f"\n{idx}/{len(cats)} → [[Category:{cat}]]")
        try:
            process(cat)
        except Exception as e:
            print(f"  !! unexpected error: {e}")
        time.sleep(THROTTLE)
    print("\nDone.")

if __name__ == "__main__":
    main()
