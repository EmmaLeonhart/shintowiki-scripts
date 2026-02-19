#!/usr/bin/env python3
"""
category_sweep_single_bot.py (immediate deletion, improved)
===========================================================
For every C in [[Category:Categories with 1 members]]:
 1. Skip if C’s name begins with a digit or contains “ in ” or “ of ”.
 2. If C has exactly one member P:
    a. Remove any [[Category:C]] (with or without sortkey) from P and save.
    b. Immediately re-fetch C’s members; if now zero, delete C.
"""

import re, time, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 1.0

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

def fetch_members(cat_title):
    """Return list of categorymembers for the given cat_title."""
    members, cont = [], {}
    while True:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": cat_title,
            "cmlimit": "max"
        }
        params.update(cont)
        data = site.api(**params)
        members.extend(data["query"]["categorymembers"])
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return members

def safe_save(page, new_text, summary):
    old = page.text()
    if old == new_text:
        print("    • nothing to save")
        return False
    try:
        page.save(new_text, summary=summary)
        print("    ✓ saved")
        return True
    except APIError as e:
        print(f"    ! save failed: {e.code}")
        return False

def safe_delete(page, reason):
    try:
        page.delete(reason=reason, watch=False)
        print(f"    ✓ deleted")
        return True
    except APIError as e:
        print(f"    ! delete failed: {e.code}")
        return False

def main():
    root_cat = "Category:Categories with 1 members"
    all_cats = fetch_members(root_cat)
    total = len(all_cats)

    for idx, info in enumerate(all_cats, 1):
        cat_title = info["title"]                # e.g. "Category:Foo"
        cat_name  = cat_title.split(":", 1)[1]   # e.g. "Foo"
        print(f"{idx}/{total} → [[{cat_title}]]")

        # 1) Skip by name rule
        if re.match(r"^\d", cat_name) or " in " in cat_name or " of " in cat_name:
            print("  • skipped by naming rule\n")
            continue

        # 2) Fetch its members
        members = fetch_members(cat_title)
        if len(members) != 1:
            print(f"  • has {len(members)} members; skipping\n")
            continue

        # That sole member
        page_title = members[0]["title"]
        page = site.pages[page_title]
        print(f"  • sole member is [[{page_title}]]")

        # 3) Remove the category link (with optional sort key)
        cat_link_re = re.compile(
            rf"\[\[Category:{re.escape(cat_name)}(?:\|[^\]]*)?\]\]",
            flags=re.IGNORECASE
        )
        old_text = page.text()
        new_text = cat_link_re.sub("", old_text).rstrip() + "\n"
        if old_text == new_text:
            print("    • category link not found on page\n")
            continue

        print(f"  • removing [[{cat_title}]] from [[{page_title}]]")
        if safe_save(page, new_text, f"Bot: remove sole member from [[{cat_title}]]"):
            time.sleep(THROTTLE)
        else:
            print("    ! failed to save change\n")
            continue

        # 4) Immediately re-fetch the category members
        remaining = fetch_members(cat_title)
        if not remaining:
            print(f"  • [[{cat_title}]] is now empty → deleting it")
            cat_page = site.pages[cat_title]
            safe_delete(cat_page, "Bot: delete empty single-member category")
        else:
            print(f"  • [[{cat_title}]] still has {len(remaining)} member(s); left intact")

        print()

    print("All done.")

if __name__ == "__main__":
    main()
