"""
batch_delete_draft_pages.py
============================
Deletes pages listed in pages_to_delete.txt
and any existing pages on Shinto Wiki whose titles begin with "draft:" (case-insensitive prefix).

Configure USERNAME/PASSWORD, then run:
    python batch_delete_draft_pages.py
"""
import os
import sys
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ─────────────────────────────────────────────────
PAGES_FILE = 'pages_to_delete.txt'  # list of specific page titles to delete
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_2]'
THROTTLE   = 1.0  # seconds between deletions

# ─── HELPER FUNCTIONS ───────────────────────────────────────────────
def load_titles(file_path):
    if not os.path.exists(file_path):
        open(file_path, 'w', encoding='utf-8').close()
        print(f"Created empty {file_path}; add page titles and re-run.")
        sys.exit(0)
    with open(file_path, 'r', encoding='utf-8') as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith('#')]


def delete_page(site, title):
    page = site.pages[title]
    try:
        if not page.exists:
            print(f"Page '{title}' does not exist; skipping.")
            return
        page.delete(reason='Bot: batch delete', watch=False)
        print(f"Deleted '{title}'")
    except APIError as e:
        print(f"Failed to delete '{title}': {e.code} - {e.info}")
    except Exception as e:
        print(f"Error deleting '{title}': {e}")

# ─── MAIN EXECUTION ─────────────────────────────────────────────────
if __name__ == '__main__':
    # login
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    #print(f"Logged in to {WIKI_URL} as {site.userinfo.get('name')}")

    # delete specific pages
    titles = load_titles(PAGES_FILE)
    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{len(titles)} Deleting listed page: '{title}'")
        delete_page(site, title)
        time.sleep(THROTTLE)

    # delete all pages beginning with 'draft:' in main namespace
    print("\nDeleting all pages with titles starting with 'draft:'...")
    count = 0
    for page in site.allpages(namespace=0, start='draft:'):
        if page.name.lower().startswith('draft:'):
            count += 1
            print(f"Deleting draft page: '{page.name}'")
            delete_page(site, page.name)
            time.sleep(THROTTLE)
    if count == 0:
        print("No 'draft:' pages found to delete.")

    print("Done batch delete.")
