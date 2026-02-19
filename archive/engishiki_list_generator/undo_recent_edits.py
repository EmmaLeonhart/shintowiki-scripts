#!/usr/bin/env python3
"""
undo_recent_edits.py

Queries the wiki contribution history for the past 90 minutes and reverts all edits.
Uses the wiki API to get user contributions, then reverts each edit to its previous state.
"""

import os
import requests
import time
import sys
import io
from datetime import datetime, timedelta

# Handle UTF-8 encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_API = "https://shinto.miraheze.org/w/api.php"

USER = os.getenv("WIKI_USER") or "Immanuelle"
PASS = os.getenv("WIKI_PASS") or "[REDACTED_SECRET_2]"

S = requests.Session()
S.headers["User-Agent"] = "ShikinaishaRevertBot/0.1"

def wiki_login():
    """Login to the wiki and return CSRF token."""
    t = S.get(WIKI_API, params={
        "action": "query", "meta": "tokens",
        "type": "login", "format": "json"}).json()
    S.post(WIKI_API, data={
        "action": "login", "lgname": USER, "lgpassword": PASS,
        "lgtoken": t["query"]["tokens"]["logintoken"], "format": "json"})
    return S.get(WIKI_API, params={
        "action": "query", "meta": "tokens", "format": "json"}).json() \
             ["query"]["tokens"]["csrftoken"]

def get_user_contributions(username, hours=90):
    """Get all contributions by user in the past N hours."""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    cutoff_str = cutoff_time.isoformat() + "Z"

    contributions = []
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": username,
        "ucprop": "title|ids|timestamp|comment",
        "uclimit": "500",
        "format": "json"
    }

    while True:
        r = S.get(WIKI_API, params=params).json()

        if "error" in r:
            print(f"[ERROR] API error: {r['error']}")
            return contributions

        if "query" not in r or "usercontribs" not in r["query"]:
            print(f"[ERROR] Unexpected API response: {r}")
            return contributions

        for contrib in r["query"]["usercontribs"]:
            contrib_time = contrib["timestamp"]
            # Stop if we've gone past 90 minutes
            if contrib_time < cutoff_str:
                return contributions
            contributions.append({
                "title": contrib["title"],
                "revid": contrib["revid"]
            })

        if "continue" not in r:
            break
        params["uccontinue"] = r["continue"]["uccontinue"]

    return contributions

def get_revision_before_cutoff(page_title, cutoff_timestamp):
    """Get the content of a page from before the cutoff time."""
    r = S.get(WIKI_API, params={
        "action": "query",
        "titles": page_title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvlimit": "50",
        "format": "json"
    }).json()

    try:
        pages = r["query"]["pages"]
        for page_id, page in pages.items():
            if "revisions" in page:
                # Sort revisions chronologically
                revisions = sorted(page["revisions"], key=lambda x: x["timestamp"])
                # Find the first revision before the cutoff
                for rev in revisions:
                    if rev["timestamp"] < cutoff_timestamp:
                        return rev.get("*", "")
                # If no revision before cutoff, return None (page was created after cutoff)
                return None
    except (KeyError, TypeError):
        return None
    return None

def revert_page_content(page_title, old_content, token):
    """Restore a page to its previous content."""
    if old_content is None:
        # Page was created by bot, set to empty
        old_content = ""

    r = S.post(WIKI_API, data={
        "action": "edit",
        "title": page_title,
        "text": old_content,
        "token": token,
        "format": "json",
        "summary": "Bot: Reverting edits from past 90 minutes"
    }).json()

    if "error" in r:
        print(f"[ERROR] {page_title}: {r['error']}")
        return False

    print(f"[OK] {page_title}")
    time.sleep(1)  # Rate limit
    return True

if __name__ == "__main__":
    print("[INFO] Logging in...")
    csrf = wiki_login()

    cutoff_time = datetime.utcnow() - timedelta(hours=90)
    cutoff_timestamp = cutoff_time.isoformat() + "Z"
    print(f"[INFO] Cutoff time: {cutoff_timestamp}")

    print("[INFO] Querying user contributions from past 90 minutes...")
    contributions = get_user_contributions(USER, hours=90)
    print(f"[INFO] Found {len(contributions)} edits to revert")

    print("[INFO] Starting revert process...")
    count = 0
    for contrib in contributions:
        title = contrib["title"]

        old_content = get_revision_before_cutoff(title, cutoff_timestamp)

        if revert_page_content(title, old_content, csrf):
            count += 1

    print(f"\n[DONE] Reverted {count}/{len(contributions)} edits")
