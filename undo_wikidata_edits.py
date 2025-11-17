#!/usr/bin/env python3
"""
undo_wikidata_edits.py
======================
Undo the most recent bot edits from add_wikidata_to_ill_templates.py
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
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
    "Hour deities",
    "Hinoki Shrine",
    "Hachimanyama Kofun",
    "Futajiiri-hime",
    "Furogu Shrine",
    "Fukashi Shrine",
    "First hour of the night (Ancient Egypt)",
    "First hour of the day (Ancient Egypt)",
    "Festival Calendar of the Acrobat Troupe",
    "Ebers calendar",
    "Djehuti",
    "Clock (Faberge egg)",
    "Chonsu (month)",
    "Cheri-cheped-seret",
    "Cheri-cheped-Kenmut",
    "Cheret-waret",
    "Chentet-heret",
    "Chau (Decan)",
    "Chatiu demons",
    "Book of the Night",
    "Book of the Day",
    "Bastet Festival",
    "Baktiu",
    "Ancient Egyptian Lunar Calendar",
    "Ancient Egyptian Day",
    "Ancient Egyptian cryptography",
    "Acronychic",
    "Abesches",
    "Ab (decan)",
    "A2 Decan Lists",
    "A1 Decan Lists",
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

            # Get the revision history
            revisions = list(pg.revisions(limit=2))

            if len(revisions) < 2:
                print(f"  [SKIP] not enough revisions")
                continue

            # The first revision in the list is the most recent
            most_recent = revisions[0]
            previous = revisions[1]

            # Get the text from the previous revision
            previous_text = previous['*']

            # Save with undo summary
            try:
                pg.save(previous_text, summary=f"Bot: Undo previous edit (revert to revision {previous['revid']})")
                count += 1
                print(f"  [DONE] reverted")
            except APIError as e:
                print(f"  [FAILED] save failed: {e.code}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print(f"\nTotal pages reverted: {count}")

if __name__=='__main__':
    main()
