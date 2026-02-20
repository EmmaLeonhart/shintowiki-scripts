#!/usr/bin/env python3
"""
revert_by_timestamp.py

Reverts all wiki pages to their state before a specific timestamp (19:38 PST).
Uses MediaWiki's powerful revert-based approach to handle this efficiently.
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

# Cutoff time: 19:38 PST = 03:38 UTC (next day)
# For 2025-11-20 19:38 PST = 2025-11-21 03:38 UTC
CUTOFF_TIMESTAMP = "2025-11-21T03:38:00Z"

def wiki_login():
    """Login to the wiki and return CSRF token."""
    t = S.get(WIKI_API, params={
        "action": "query", "meta": "tokens",
        "type": "login", "format": "json"}, timeout=30).json()
    S.post(WIKI_API, data={
        "action": "login", "lgname": USER, "lgpassword": PASS,
        "lgtoken": t["query"]["tokens"]["logintoken"], "format": "json"}, timeout=30)
    return S.get(WIKI_API, params={
        "action": "query", "meta": "tokens", "format": "json"}, timeout=30).json() \
             ["query"]["tokens"]["csrftoken"]

def get_user_contributions(username, cutoff_ts):
    """Get all contributions by user after the cutoff timestamp."""
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
        r = S.get(WIKI_API, params=params, timeout=30).json()

        if "error" in r:
            print(f"[ERROR] API error: {r['error']}")
            break

        if "query" not in r or "usercontribs" not in r["query"]:
            break

        for contrib in r["query"]["usercontribs"]:
            contrib_time = contrib["timestamp"]
            # Stop if we've gone past the cutoff
            if contrib_time < cutoff_ts:
                return contributions
            contributions.append({
                "title": contrib["title"],
                "revid": contrib["revid"],
                "timestamp": contrib_time
            })

        if "continue" not in r:
            break
        params["uccontinue"] = r["continue"]["uccontinue"]

    return contributions

def get_revision_content_before_cutoff(page_title, cutoff_ts):
    """Get the content of the last revision before the cutoff timestamp."""
    r = S.get(WIKI_API, params={
        "action": "query",
        "titles": page_title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvlimit": "50",
        "format": "json"
    }, timeout=30).json()

    try:
        pages = r["query"]["pages"]
        for page in pages.values():
            if "revisions" in page:
                revisions = sorted(page["revisions"], key=lambda x: x["timestamp"], reverse=True)
                for rev in revisions:
                    if rev["timestamp"] < cutoff_ts:
                        return rev.get("*", "")
    except (KeyError, TypeError):
        pass
    return None

def restore_page_content(page_title, content, token):
    """Restore a page to specific content."""
    if content is None:
        content = ""

    r = S.post(WIKI_API, data={
        "action": "edit",
        "title": page_title,
        "text": content,
        "token": token,
        "format": "json",
        "summary": "Reverting edits made after 19:38 PST"
    }).json()

    if "error" in r:
        return False
    return True

if __name__ == "__main__":
    print(f"[INFO] Cutoff timestamp: {CUTOFF_TIMESTAMP}")
    print("[INFO] Logging in...")
    csrf = wiki_login()

    print("[INFO] Querying user contributions...")
    contributions = get_user_contributions(USER, CUTOFF_TIMESTAMP)

    # Group by page to get unique pages
    unique_pages = {}
    for contrib in contributions:
        if contrib["title"] not in unique_pages:
            unique_pages[contrib["title"]] = contrib

    print(f"[INFO] Found {len(contributions)} edits affecting {len(unique_pages)} unique pages")
    print("[INFO] Starting revert process...")

    count = 0
    for title in unique_pages:
        content_before = get_revision_content_before_cutoff(title, CUTOFF_TIMESTAMP)
        if restore_page_content(title, content_before, csrf):
            print(f"[OK] {title}")
            count += 1
        else:
            print(f"[SKIP] {title}")
        time.sleep(0.5)

    print(f"\n[DONE] Reverted {count} pages out of {len(unique_pages)}")
