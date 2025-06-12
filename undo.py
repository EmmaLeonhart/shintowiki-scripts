"""
undo_last_edit_bot.py (v2)
===========================
Reads page titles from *pages.txt* and undoes the last *N* edits defined by `UNDO_COUNT`.

Configuration:
- `UNDO_COUNT`: number of recent edits to revert (1 = only the last edit)

For each page:
1. Fetch the `UNDO_COUNT+1` most recent revisions.
2. Collect the top `UNDO_COUNT` revision IDs.
3. Loop through them in order (newest first), calling `edit` with `undo=<revID>`.
4. Log each undo action.

Requirements: `rollback` or edit rights. Usage:
  python undo_last_edit_bot.py
"""

import os
import sys
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'          # leading/trailing slash
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
PAGES_TXT  = 'pages.txt'     # list of page titles
THROTTLE   = 1.0             # seconds between API calls
UNDO_COUNT = 3               # how many recent edits to undo per page

# ─── LOGIN ──────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
#user = site.userinfo.get('name', USERNAME)
#print(f"Logged in as {user}")

# ─── HELPER: load titles ─────────────────────────────────────────────
def load_titles():
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT, 'w', encoding='utf-8').close()
        print(f"Created empty {PAGES_TXT}; add page titles and re-run.")
        sys.exit(1)
    with open(PAGES_TXT, 'r', encoding='utf-8', errors='ignore') as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

# ─── FUNCTION: undo last N edits ────────────────────────────────────
def undo_last_edits(title: str, count: int):
    page = site.pages[title]
    if not page.exists:
        print(f"   ! [[{title}]] does not exist; skipped")
        return
    try:
        # fetch count+1 revisions: newest first
        rvlimit = count + 1
        data = site.api('query', prop='revisions', titles=title,
                        rvprop='ids|user|comment', rvlimit=rvlimit, format='json')
        pages = data.get('query', {}).get('pages', {})
        info = next(iter(pages.values()), {})
        revs = info.get('revisions', [])
        if len(revs) < 2:
            print(f"   ! [[{title}]] has fewer than 2 revisions; cannot undo")
            return
        # determine how many we can undo
        to_undo = min(count, len(revs)-1)
        rev_ids = [r['revid'] for r in revs[:to_undo]]
        # perform undos sequentially
        token = site.get_token('csrf')
        for rev in rev_ids:
            summary = f"Bot: undo edit ([[Special:Diff/{rev}]])"
            site.api('edit', title=title, undo=rev, token=token, summary=summary)
            print(f"   • undone rev {rev} on [[{title}]]")
            time.sleep(THROTTLE)
    except APIError as e:
        print(f"   ! APIError on [[{title}]]: {e.code} – {e.info}")
    except Exception as e:
        print(f"   ! Error on [[{title}]]: {e}")

# ─── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    titles = load_titles()
    total = len(titles)
    for idx, title in enumerate(titles, start=1):
        print(f"{idx}/{total} — Undoing last {UNDO_COUNT} edits on [[{title}]]")
        undo_last_edits(title, UNDO_COUNT)
    print("Done!")

if __name__ == '__main__':
    main()
