#!/usr/bin/env python3
"""
undo_wikidata_edits_v3.py
==========================
Undo the most recent bot edits using direct API calls
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
# <<< credentials <<<

import os, sys, time, requests
import urllib.parse

THROTTLE = 0.5

session = requests.Session()

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

# ─── login ─────────────────────────────────────────────────────────

def login():
    # Get login token
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }
    response = session.get(API_URL, params=params)
    login_token = response.json()["query"]["tokens"]["logintoken"]

    # Login
    params = {
        "action": "clientlogin",
        "username": USERNAME,
        "password": PASSWORD,
        "logintoken": login_token,
        "loginreturnurl": "https://shinto.miraheze.org",
        "format": "json"
    }
    session.post(API_URL, data=params)
    print("Logged in")

# ─── main loop ────────────────────────────────────────────────────

def main():
    login()

    count = 0
    for page_name in pages_to_undo:
        try:
            print(f"Undoing: {page_name}")

            # Get page info and most recent revision
            params = {
                "action": "query",
                "titles": page_name,
                "prop": "revisions",
                "rvlimit": 2,
                "rvprop": "ids|user|comment",
                "format": "json"
            }
            response = session.get(API_URL, params=params)
            pages = response.json()["query"]["pages"]

            if not pages:
                print(f"  [SKIP] page not found")
                continue

            page = next(iter(pages.values()), None)
            if not page or "revisions" not in page or len(page["revisions"]) < 2:
                print(f"  [SKIP] cannot find revisions")
                continue

            most_recent_rev = page["revisions"][0]["revid"]
            previous_rev = page["revisions"][1]["revid"]

            # Get CSRF token
            params = {
                "action": "query",
                "meta": "tokens",
                "type": "csrf",
                "format": "json"
            }
            response = session.get(API_URL, params=params)
            csrf_token = response.json()["query"]["tokens"]["csrftoken"]

            # Undo the edit
            params = {
                "action": "edit",
                "title": page_name,
                "undo": most_recent_rev,
                "undoafter": previous_rev,
                "summary": "Bot: Undo bad edit",
                "token": csrf_token,
                "format": "json"
            }
            response = session.post(API_URL, data=params)
            result = response.json()

            if "edit" in result and result["edit"]["result"] == "Success":
                count += 1
                print(f"  [DONE] reverted")
            else:
                print(f"  [FAILED] {result}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print(f"\nTotal pages reverted: {count}")

if __name__=='__main__':
    main()
