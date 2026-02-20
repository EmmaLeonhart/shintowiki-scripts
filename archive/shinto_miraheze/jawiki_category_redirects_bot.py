#!/usr/bin/env python3
"""
jawiki_category_redirects_bot.py
================================
For every category C in Category:Jawiki linked categories:
  • If C’s page text contains [[ja:Category:J]],
    create (or update) Category:J as a redirect to C,
    and tag it with [[Category:jawiki redirect categories]].
"""

import re, time, mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
WIKI_URL     = "shinto.miraheze.org"
WIKI_PATH    = "/w/"
USERNAME     = "Immanuelle"
PASSWORD     = "[REDACTED_SECRET_2]"
SOURCE_CAT   = "Category:Jawiki linked categories"
REDIRECT_TAG = "[[Category:jawiki redirect categories]]"
THROTTLE     = 1.0  # seconds between edits

# ─── LOGIN ─────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME!r}")

# ─── HELPERS ───────────────────────────────────────────────────────
def fetch_category_members(cat_title):
    """Return a list of dicts for each member of cat_title."""
    members = []
    cont = {}
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

def safe_save(page, text, summary):
    """Save text to page if it’s changed, handling conflicts."""
    try:
        old = page.text()
    except Exception as e:
        print(f"    ! could not fetch [[{page.name}]] text: {e}")
        return False
    if old.strip() == text.strip():
        print("    • no change needed")
        return False
    try:
        page.save(text, summary=summary)
        print("    ✓ saved")
        return True
    except APIError as e:
        print(f"    ! APIError saving [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"    ! unexpected error saving [[{page.name}]]: {e}")
    return False

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    print(f"Fetching members of [[{SOURCE_CAT}]]…")
    cats = fetch_category_members(SOURCE_CAT)
    print(f"Found {len(cats)} categories to process.\n")

    # regex to find [[ja:Category:...]]
    IWIKILINK = re.compile(r"\[\[\s*ja:Category:([^\]\|]+)\]\]", re.IGNORECASE)

    for idx, entry in enumerate(cats, 1):
        cat_title = entry["title"]  # e.g. "Category:Foo"
        print(f"{idx}/{len(cats)} → [[{cat_title}]]")

        page = site.pages[cat_title]
        try:
            text = page.text()
        except Exception as e:
            print(f"  ! could not fetch [[{cat_title}]]: {e}\n")
            continue

        m = IWIKILINK.search(text)
        if not m:
            print("  • no [[ja:Category:…]] link found; skipped\n")
            continue

        ja_name = m.group(1).strip()  # e.g. "兵庫県の旧県社"
        redirect_cat = f"Category:{ja_name}"
        redirect_page = site.pages[redirect_cat]

        # If it already exists and is the right redirect, skip.
        if redirect_page.exists:
            tgt = None
            try:
                tgt = redirect_page.redirects_to and redirect_page.redirects_to.name
            except Exception:
                pass
            if tgt == cat_title:
                print(f"  • [[{redirect_cat}]] already redirects to [[{cat_title}]]; skipped\n")
                continue
            else:
                print(f"  • [[{redirect_cat}]] exists but not pointing to us; updating…")
        else:
            print(f"  • creating redirect [[{redirect_cat}]] → [[{cat_title}]]")

        # build redirect wikitext
        redirect_wikitext = (
            f"#REDIRECT [[{cat_title}]]\n\n"
            f"{REDIRECT_TAG}\n"
        )

        # save or overwrite
        safe_save(redirect_page, redirect_wikitext,
                  f"Bot: create ja-wiki redirect for [[{cat_title}]]")
        time.sleep(THROTTLE)
        print()

    print("Done.")

if __name__ == "__main__":
    main()
