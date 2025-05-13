"""
orphaned_redirect_cleanup.py
=============================
Scan all main‑namespace pages starting at “ś” and delete any orphaned or self‑pointing redirects.

Usage:
  - Configure credentials below
  - Run: python orphaned_redirect_cleanup.py
"""
import time
import re
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
WIKI_HOST   = 'shinto.miraheze.org'
WIKI_PATH   = '/w/'
USERNAME    = 'Immanuelle'
PASSWORD    = '[REDACTED_SECRET_1]'
START_TITLE = ''       # begin enumeration at this prefix
THROTTLE    = 0.5       # seconds between operations

# ─── LOGIN ────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")

# ─── HELPERS ─────────────────────────────────────────────────────
def has_backlinks(page):
    """Return True if page has any backlinks."""
    try:
        for _ in page.backlinks(limit=1):
            return True
    except Exception:
        pass
    return False

def get_redirect_target(page):
    """Extract the redirect target title from page text."""
    try:
        txt = page.text()
    except Exception:
        return None
    m = re.match(r'(?i)^#redirect\s*\[\[:?([^\]|]+)', txt)
    if m:
        return m.group(1).strip()
    return None

# ─── REDIRECT CLEANUP ────────────────────────────────────────────
def delete_orphan_or_self_redirect(page) -> bool:
    """Delete page if it's a redirect with no backlinks, or a self‑redirect."""
    if not page.redirect:
        return False
    target = get_redirect_target(page)
    # if redirect target equals self
    if target and target == page.name:
        try:
            page.delete(reason='Bot: delete self‑redirect', watch=False)
            print(f"  • Deleted self‑redirect [[{page.name}]]")
            return True
        except APIError as e:
            print(f"  ! APIError deleting self‑redirect [[{page.name}]]: {e.code}")
        except Exception as e:
            print(f"  ! Error deleting self‑redirect [[{page.name}]]: {e}")
        return False
    # otherwise, orphan redirect if no backlinks
    if has_backlinks(page):
        print(f"  ↳ [[{page.name}]] has backlinks; kept.")
        return False
    try:
        page.delete(reason='Bot: delete orphaned redirect', watch=False)
        print(f"  • Deleted orphaned redirect [[{page.name}]]")
        return True
    except APIError as e:
        print(f"  ! APIError deleting orphaned redirect [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"  ! Error deleting orphaned redirect [[{page.name}]]: {e}")
    return False

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    print(f"Scanning mainspace pages from '{START_TITLE}' for redirects to delete...")
    for idx, page in enumerate(site.allpages(namespace=0, start=START_TITLE), start=1):
        print(f"{idx}: [[{page.name}]]", end='')
        if delete_orphan_or_self_redirect(page):
            # deletion printed inside
            pass
        else:
            print('')
        time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()
