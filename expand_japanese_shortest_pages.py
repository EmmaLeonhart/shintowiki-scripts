#!/usr/bin/env python3
"""
expand_japanese_shortest_pages.py
==================================
For pages in [[Category:1000 shortest pages as of Nov 16, 2025]]:
1. Extract the jawiki interwiki link (e.g., [[ja:よさこい祭り]])
2. If it exists, append {{Expand Japanese|TITLE|date=November 2025}} to the beginning
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re
from mwclient.errors import APIError

CATEGORY = "1000 shortest pages as of Nov 16, 2025"
THROTTLE = 0.5

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# ─── extract jawiki title ─────────────────────────────────────────

def extract_jawiki_title(text: str) -> str:
    """Extract the Japanese Wikipedia page title from interwiki links"""
    # Look for [[ja:...]]
    match = re.search(r'\[\[ja:([^\]]+)\]\]', text)
    if match:
        return match.group(1)
    return None

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in")

    # Get all pages in the category
    cat = s.pages[f"Category:{CATEGORY}"]

    if not cat.exists:
        print(f"[ERROR] Category '{CATEGORY}' does not exist")
        return

    print(f"[INFO] Processing pages in Category:{CATEGORY}")

    count = 0
    for pg in cat:
        # Only process main namespace articles
        if pg.namespace != 0:
            print(f"[SKIP] {pg.name} - not in main namespace")
            continue

        try:
            print(f"Processing: {pg.name}")
            text = pg.text()

            # Extract jawiki title
            ja_title = extract_jawiki_title(text)

            if not ja_title:
                print(f"  [SKIP] no jawiki interwiki found")
                continue

            # Check if the template is already there
            if "{{Expand Japanese" in text:
                print(f"  [SKIP] template already present")
                continue

            # Create the template
            template = f"{{{{Expand Japanese|{ja_title}|date=November 2025}}}}\n"

            # Prepend to the beginning of the page
            new_text = template + text

            # Save the page
            try:
                pg.save(new_text, summary="Bot: Add Expand Japanese template from jawiki interwiki")
                count += 1
                print(f"  [DONE] added template with ja_title: {ja_title}")
            except APIError as e:
                print(f"  [FAILED] save failed: {e.code}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print(f"\nTotal pages updated: {count}")

if __name__=='__main__':
    main()
