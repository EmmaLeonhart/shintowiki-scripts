#!/usr/bin/env python3
"""
category_merge_bot.py  –  merge one category into another
---------------------------------------------------------
Usage:
    python category_merge_bot.py "Old Category" "New Category"
Things it does (with admin rights):

1.  Ensure raw names are treated as Category:… .
2.  Copy the wikitext of *both* pages for later re-save.
3.  Delete the target (New) page (keeps history in the archive).
4.  Move Category:Old → Category:New (keeps a redirect).
5.  Undelete the earlier history of Category:New.
6.  Rewrite every page that still links to Category:Old so it
    now uses Category:New.
7.  Append the previously-saved wikitext of both pages and save.
"""

import sys, time, re, mwclient, requests
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE  = 0.4  # seconds between edits

# ─── UTILS ─────────────────────────────────────────────────────────
def cat_title(raw: str) -> str:
    return raw[9:] if raw.lower().startswith("category:") else raw

def replace_cat_on_page(page, old, new):
    txt = page.text()
    pat = re.compile(rf"\[\[\s*Category:{re.escape(old)}([^\]]*)\]\]", re.I)
    if not pat.search(txt):
        return
    new_txt = pat.sub(f"[[Category:{new}\\1]]", txt)
    if new_txt == txt:
        return
    page.save(new_txt,
              summary=f"Bot: merge {old} → {new}",
              minor=True)
    print("      •", page.name)
    time.sleep(THROTTLE)

def delete_page(page, reason):
    if page.exists:
        try:
            page.delete(reason=reason, watch=False)
            print("    • deleted", page.name)
        except APIError as e:
            sys.exit(f"Cannot delete {page.name}: {e.code}")

def undelete_all(site, title, reason):
    token = site.get_token('csrf')
    # undelete with timestamps='' means restore all revisions
    site.api(action='undelete', title=title,
             reason=reason, token=token)
    print("    • undeleted history for", title)

# ─── MAIN ──────────────────────────────────────────────────────────
def main(old_raw, new_raw):
    old_cat = cat_title(old_raw)
    new_cat = cat_title(new_raw)
    old_full = f"Category:{old_cat}"
    new_full = f"Category:{new_cat}"

    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    old_pg = site.pages[old_full]
    new_pg = site.pages[new_full]

    if not old_pg.exists:
        sys.exit("Old category does not exist!")

    # copy wikitext BEFORE doing anything
    old_text = old_pg.text()
    new_text = new_pg.text() if new_pg.exists else ""

    # 1. delete New (so title free, history in archive)
    delete_page(new_pg, "Bot: prepare merge target")

    # 2. move Old → New
    try:
        old_pg.move(new_full, reason="Bot: merge categories",
                    move_talk=True)
        print(f"✓ moved {old_full} → {new_full}")
    except APIError as e:
        sys.exit("Move failed: " + e.code)

    # after move, old_pg is now a redirect; fetch real new page object
    new_pg = site.pages[new_full]

    # 3. undelete former history (if any)
    try:
        undelete_all(site, new_full, "Bot: merge histories")
    except APIError as e:
        # if there was no deleted history this returns badtitle → ignore
        if e.code != "cantundelete":
            sys.exit("Undelete failed: " + e.code)

    # 4. rewrite residual pages still pointing to old title
    members = site.api(action='query', list='categorymembers',
                       cmtitle=old_full, cmtype='page',
                       cmlimit='max', format='json')['query']['categorymembers']
    for mem in members:
        replace_cat_on_page(site.pages[mem['title']], old_cat, new_cat)

    # 5. append wikitexts and save
    merged = (new_text.rstrip() + "\n" + old_text).rstrip() + "\n"
    new_pg.save(merged,
                summary="Bot: merge wikitext from both categories")
    print("✓ final merged content saved")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python category_merge_bot.py 'Old' 'New'")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
