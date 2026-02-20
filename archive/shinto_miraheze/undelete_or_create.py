"""
undelete_or_create_bot.py
=========================
Reads titles from pages.txt. For each title:
 1. Attempts to undelete all deleted revisions (via API).
    - On **any** failure, proceeds to create the page if it does not exist.
 2. If creation is needed, the new page content is:
      [[Category:Uncategorized categories made on YYYY-MM-DD]]

Configure USERNAME/PASSWORD, list titles in pages.txt, then run:
    python undelete_or_create_bot.py
"""
import os
import sys
import time
from datetime import datetime
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ─────────────────────────────────────────────────
PAGES_FILE  = 'pages.txt'
WIKI_URL    = 'shinto.miraheze.org'
WIKI_PATH   = '/w/'
USERNAME    = 'Immanuelle'
PASSWORD    = '[REDACTED_SECRET_2]'
THROTTLE    = 0.5  # seconds between operations

# ─── LOAD TITLES ────────────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    titles = load_titles(PAGES_FILE)
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    #print(f"Logged in as {site.userinfo.get('name')}")
    token = site.get_token('csrf')

    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{len(titles)} → [[{title}]]")
        page = site.pages[title]
        # Skip existing pages entirely
        if page.exists:
            print(f"   ↳ [[{title}]] already exists; skipped.")
            time.sleep(THROTTLE)
            continue

        # Attempt undelete on missing page
        try:
            site.api('undelete', title=title, token=token, reason='Bot: restore deleted revisions')
            print(f"  • Restored deleted revisions for [[{title}]]")
        except APIError as e:
            print(f"  ! Undelete failed ([[{title}]]): {e.code} – creating new page.")
            # Create placeholder since page is missing
            date_str = datetime.now().strftime('%Y-%m-%d')
            cat = f"Category:Uncategorized categories made on {date_str}"
            content = f"[[{cat}]]"
            try:
                page.save(content, summary='Bot: create uncategorized placeholder')
                print(f"  • Created new page [[{title}]] with category {cat}")
            except APIError as e2:
                print(f"  ! APIError creating [[{title}]]: {e2.code}")
            except Exception as e2:
                print(f"  ! Error creating [[{title}]]: {e2}")
        # Throttle
        time.sleep(THROTTLE)

    print("Done processing.")

if __name__ == '__main__':
    main()
