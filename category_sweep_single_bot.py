#!/usr/bin/env python3
"""
category_sweep_single_bot.py
=============================
For every category C in [[Category:Categories with 1 members]]:

 1. Skip C if its name (after “Category:”) begins with a digit,
    or contains “ in ” or “ of ”.
 2. Otherwise, fetch its single member P.
 3. Remove the tag [[Category:C]] from P (if present).
 4. Save P with summary "Bot: remove sole‐member from single‐member category".

Requires: import, read+edit rights on the wiki.
"""

import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
THROTTLE  = 1.0   # seconds between saves

# ─── LOGIN ──────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}\n")

# ─── HELPERS ────────────────────────────────────────────────────────
def fetch_category_members(catpage):
    """Return the list of all members of category page `catpage`."""
    members = []
    cm_cont = {}
    while True:
        params = {
            "action":      "query",
            "format":      "json",
            "list":        "categorymembers",
            "cmtitle":     catpage,
            "cmlimit":     "max"
        }
        params.update(cm_cont)
        data = site.api(**params)
        members.extend(data["query"]["categorymembers"])
        if "continue" in data:
            cm_cont = data["continue"]
        else:
            break
    return members

def safe_save(page, new_text, summary):
    """Save if changed, swallow edit conflicts & API errors."""
    try:
        old = page.text()
    except Exception:
        print(f"    ! could not fetch [[{page.name}]]; skipping")
        return False
    if old == new_text:
        return False
    try:
        page.save(new_text, summary=summary)
        return True
    except APIError as e:
        if e.code == "editconflict":
            print(f"    ! edit conflict on [[{page.name}]]; skipped")
            return False
        print(f"    ! APIError on [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"    ! error saving [[{page.name}]]: {e}")
    return False

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    ROOT_CAT = "Category:Categories with 1 members"
    print(f"Fetching single-member categories from [[{ROOT_CAT}]]…")
    cats = fetch_category_members(ROOT_CAT)

    for idx, catinfo in enumerate(cats, 1):
        catname = catinfo["title"]               # e.g. "Category:Foo"
        short   = catname.split(":",1)[1]        # "Foo"
        print(f"{idx}/{len(cats)} → [[{catname}]]")

        # skip if short begins with digit or contains " in " or " of "
        if re.match(r'^\d', short) or " in " in short or " of " in short:
            print(f"  • skipping [[{catname}]] (name starts with digit or contains ' in ' / ' of ')\n")
            continue

        members = fetch_category_members(catname)
        if len(members) != 1:
            print(f"  ! expected 1 member, found {len(members)}; skipping\n")
            continue

        m = members[0]
        member_title = m["title"]
        page = site.pages[member_title]
        try:
            text = page.text()
        except Exception:
            print(f"  ! could not fetch [[{member_title}]]; skipping\n")
            continue

        # remove the tag [[Category:Foo]] (case-insensitive)
        pattern = re.compile(rf"\[\[Category:{re.escape(short)}\]\]", re.IGNORECASE)
        new_text = pattern.sub("", text).rstrip() + "\n"

        if new_text == text:
            print(f"  • [[{member_title}]] did not have [[{catname}]]; nothing to do\n")
            continue

        print(f"  • removing [[{catname}]] from [[{member_title}]]")
        if safe_save(page, new_text, f"Bot: remove sole member from [[{catname}]]"):
            time.sleep(THROTTLE)
            print(f"    ✓ saved [[{member_title}]]\n")
        else:
            print(f"    ! save failed [[{member_title}]]\n")

    print("All done.")

if __name__ == "__main__":
    main()
