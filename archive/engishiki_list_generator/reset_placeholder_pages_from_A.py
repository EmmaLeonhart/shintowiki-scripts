#!/usr/bin/env python3
"""
reset_placeholder_pages_from_A.py

Overwrites every page in [[Category:Wikidata generated shikinaisha pages]]
starting from letter A onwards with a placeholder message.
"""

import os
import requests
import time
import sys
import io

# Handle UTF-8 encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_API = "https://shinto.miraheze.org/w/api.php"

USER = os.getenv("WIKI_USER") or "Immanuelle"
PASS = os.getenv("WIKI_PASS") or "[REDACTED_SECRET_2]"

S = requests.Session()
S.headers["User-Agent"] = "ShikinaishaPlaceholderBot/0.1"

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

def get_category_members(cat):
    """Get all pages in a category."""
    cont = ""
    members = []
    while True:
        r = S.get(WIKI_API, params={
            "action": "query", "list": "categorymembers", "cmtitle": cat,
            "cmlimit": "500", "cmcontinue": cont, "format": "json"}).json()
        for m in r["query"]["categorymembers"]:
            members.append(m["title"])
        if "continue" not in r:
            break
        cont = r["continue"]["cmcontinue"]
    return members

def has_protected_category(title):
    """Check if page has LINKED FROM WIKIDATA DO NOT OVERWRITE category."""
    r = S.get(WIKI_API, params={
        "action": "query", "titles": title, "prop": "categories",
        "format": "json"}).json()
    try:
        pages = r["query"]["pages"]
        for page in pages.values():
            if "categories" in page:
                for cat in page["categories"]:
                    if "LINKED FROM WIKIDATA DO NOT OVERWRITE" in cat["title"]:
                        return True
    except (KeyError, TypeError):
        pass
    return False

def overwrite_page(title, token):
    """Overwrite a page with placeholder content."""
    # Skip pages with protected category
    if has_protected_category(title):
        print(f"[SKIP] {title} (protected)")
        return False

    placeholder = "PLACEHOLDER SHIKINAISHA PAGE [[Category:Wikidata generated shikinaisha pages]]"

    r = S.post(WIKI_API, data={
        "action": "edit", "title": title, "text": placeholder, "token": token,
        "format": "json", "summary": "Bot: Reset placeholder for wiki page generation"}).json()

    if "error" in r:
        print(f"[ERROR] {title}: {r['error']}")
        return False

    print(f"[OK] {title}")
    time.sleep(1)  # Rate limit
    return True

if __name__ == "__main__":
    print("[INFO] Logging in...")
    csrf = wiki_login()

    print("[INFO] Getting category members...")
    members = get_category_members("Category:Wikidata generated shikinaisha pages")
    print(f"[INFO] Found {len(members)} pages total")

    # Filter to only pages starting with A or later
    filtered_members = [m for m in members if m[0] >= 'A']
    print(f"[INFO] Processing {len(filtered_members)} pages starting from A onwards")

    print("[INFO] Starting reset from letter A...")
    count = 0
    for title in filtered_members:
        if overwrite_page(title, csrf):
            count += 1

    print(f"\n[DONE] Reset {count}/{len(filtered_members)} pages (starting from A)")
