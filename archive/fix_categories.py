"""
category_cleanup_bot.py
=======================
Reads category titles from pages.txt and for each category:
 1. Iterates through all members (pages) of that category and removes the category link from each.
 2. Deletes the (now empty) category page.

Usage:
  - List categories (e.g. "Category:Foo") line by line in pages.txt
  - Configure credentials below
  - Run: python category_cleanup_bot.py
"""
import os
import sys
import time
import re
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE = 'pages.txt'        # list of category titles, e.g. Category:Foo
WIKI_HOST  = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
THROTTLE   = 1.0                # seconds between operations

# ─── LOAD CATEGORY TITLES ────────────────────────────────────────

def load_categories(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add Category titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]
    return lines

# ─── HELPERS ─────────────────────────────────────────────────────

def safe_save(page, new_text, summary):
    try:
        current = page.text()
    except Exception:
        return False
    if current.strip() == new_text.strip():
        return False
    try:
        page.save(new_text, summary=summary)
        return True
    except APIError as e:
        print(f"! APIError saving [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"! Error saving [[{page.name}]]: {e}")
    return False

# ─── MAIN LOOP ───────────────────────────────────────────────────

def main():
    cats = load_categories(PAGES_FILE)
    site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    for idx, cat_title in enumerate(cats, start=1):
        print(f"{idx}/{len(cats)} → [[{cat_title}]]")
        cat_page = site.pages.get(cat_title)
        if not cat_page or not cat_page.exists:
            print(f"  ! Category missing: [[{cat_title}]]; skipped.")
            continue

        # build regex to remove category link (with optional sort key)
        escaped = re.escape(cat_title.replace('Category:', ''))
        cat_link_re = re.compile(rf"\[\[Category:{escaped}(?:\|[^\]]*)?\]\]", re.IGNORECASE)

        # iterate members
        try:
            members = list(site.categories[cat_title.replace('Category:', '')])
        except Exception as e:
            print(f"  ! Failed to fetch members of [[{cat_title}]]: {e}")
            members = []

        for member in members:
            print(f"  → member [[{member.name}]]")
            try:
                text = member.text()
                new_text = cat_link_re.sub('', text)
                if safe_save(member, new_text, f"Bot: remove [[{cat_title}]] from page" ):
                    print(f"    ✓ removed category from [[{member.name}]]")
            except Exception as e:
                print(f"    ! Failed processing [[{member.name}]]: {e}")
            time.sleep(THROTTLE)

        # delete the category page
        try:
            cat_page.delete(reason='Bot: category cleanup', watch=False)
            print(f"  ✓ deleted category [[{cat_title}]]")
        except APIError as e:
            print(f"  ! APIError deleting [[{cat_title}]]: {e.code}")
        except Exception as e:
            print(f"  ! Error deleting [[{cat_title}]]: {e}")
        time.sleep(THROTTLE)

    print("All done.")

if __name__ == '__main__':
    main()
