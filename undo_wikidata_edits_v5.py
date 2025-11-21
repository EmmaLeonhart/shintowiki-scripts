#!/usr/bin/env python3
"""
undo_wikidata_edits_v5.py
==========================
Undo additional bad edits
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient
from mwclient.errors import APIError

THROTTLE = 0.5

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# Pages to undo
pages_to_undo = [
    "Menchet Festival",
    "Menchet (month)",
    "Logic of basho",
    "Kinkaku-ji arson incident",
    "King's Festival Calendar",
    "Kimigayo",
    "Khenti-khet",
    "Keta Jinja",
    "Keratuten",
    "Kenmet (Decan)",
    "Kenemu",
]

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in")

    count = 0
    for page_name in pages_to_undo:
        try:
            print(f"Undoing: {page_name}")
            pg = s.pages[page_name]

            if not pg.exists:
                print(f"  [SKIP] page does not exist")
                continue

            # Get the current page content and iterate through revisions manually
            all_revisions = []
            for rev in pg.revisions(limit=2, prop='ids|content'):
                all_revisions.append(rev)

            if len(all_revisions) < 2:
                print(f"  [SKIP] not enough revisions")
                continue

            # all_revisions[0] is the most recent
            # all_revisions[1] is the one before
            previous_content = all_revisions[1]['*']

            # Save the previous content
            try:
                pg.save(previous_content, summary="Bot: Undo bad edit from wikidata script")
                count += 1
                print(f"  [DONE] reverted to previous version")
            except APIError as e:
                print(f"  [FAILED] save failed: {e.code}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print(f"\nTotal pages reverted: {count}")

if __name__=='__main__':
    main()
