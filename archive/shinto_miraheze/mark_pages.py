"""
mark_history_import_needed_bot.py
=================================

For each backlink-list page in pages.txt (each listing exactly two pages as "# [[PageA]]" and "# [[PageB]]"),
add [[Category:pages needing proper jawiki and history import]] to each of the two listed pages.

Usage:
  - List backlink-list pages in pages.txt
  - Configure credentials below
  - Run: python mark_history_import_needed_bot.py
"""
import os
import sys
import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE   = 'pages.txt'  # list of backlink-list pages
WIKI_HOST    = 'shinto.miraheze.org'
WIKI_PATH    = '/w/'
USERNAME     = 'Immanuelle'
PASSWORD     = '[REDACTED_SECRET_2]'
CATEGORY     = 'Category:pages needing proper jawiki and history import'
THROTTLE     = 1.0          # seconds between edits

# ─── UTILITIES ────────────────────────────────────────────────────
def load_pages(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add listing pages and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    pages = load_pages(PAGES_FILE)
    site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    BACKLINK_RE = re.compile(r'^# \[\[([^\]]+)\]\]', re.MULTILINE)
    CAT_RE      = re.compile(rf"\[\[{re.escape(CATEGORY)}\]\]", re.IGNORECASE)

    for title in pages:
        print(f"Processing listing [[{title}]]...")
        page = site.pages[title]
        try:
            text = page.text()
        except Exception as e:
            print(f"  ! Could not fetch [[{title}]]: {e}")
            continue

        matches = BACKLINK_RE.findall(text)
        if len(matches) != 2:
            print(f"  – Expected 2 backlinks, found {len(matches)}; skipping.")
            continue

        for target_name in matches:
            tgt = site.pages[target_name]
            try:
                tgt_text = tgt.text()
            except Exception as e:
                print(f"  ! Could not load [[{target_name}]]: {e}")
                continue
            if CAT_RE.search(tgt_text):
                print(f"  – [[{target_name}]] already tagged; skipping.")
                continue
            new_text = tgt_text.rstrip() + f"\n[[{CATEGORY}]]\n"
            try:
                tgt.save(new_text,
                         summary=(f"Bot: mark [[{target_name}]] for proper jawiki/history import"))
                print(f"  ✓ Tagged [[{target_name}]]")
            except APIError as e:
                print(f"  ! APIError saving [[{target_name}]]: {e.code}")
            except Exception as e:
                print(f"  ! Error saving [[{target_name}]]: {e}")
            time.sleep(THROTTLE)

    print("Done.")

if __name__ == '__main__':
    main()
