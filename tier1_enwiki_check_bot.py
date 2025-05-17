#!/usr/bin/env python3
"""
tier1_enwiki_check_bot.py
==========================

Scans all subcategories of [[Category:Tier 1 Categories]] and tags those
without an English Wikipedia interwiki link by adding them to
[[Category:Tier 1 Categories with no enwiki]].

Steps:
1. Log in to Shinto Wiki via mwclient.
2. Retrieve all subcategories of "Tier 1 Categories".
3. For each subcategory:
   a. Query the page for a langlink to English (lllang=en).
   b. If none found, append [[Category:Tier 1 Categories with no enwiki]]
      to the bottom of the page (if not already present).
   c. Save with summary indicating tagging.
4. Throttle between edits to avoid rate limits.
"""
import os
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL     = "shinto.miraheze.org"
SITE_PATH    = "/w/"
USERNAME     = "Immanuelle"
PASSWORD     = "[REDACTED_SECRET_1]"
SOURCE_CAT   = "Tier 1 Categories"
TAG_CAT      = "Tier 1 Categories with no enwiki"
THROTTLE     = 0.5  # seconds between API calls/edits

# ─── MAIN TASK ──────────────────────────────────────────────────────

def main():
    # Connect and login
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    # Fetch all subcategories
    cm_params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{SOURCE_CAT}",
        "cmtype": "subcat",
        "cmlimit": "max"
    }
    members = site.api(**cm_params)["query"]["categorymembers"]

    for entry in members:
        subcat_full = entry["title"]            # e.g. "Category:Example"
        print(f"Checking {subcat_full}")

        # Check for English interwiki via langlinks
        ll_params = {
            "action": "query",
            "titles": subcat_full,
            "prop": "langlinks",
            "lllang": "en",
            "lllimit": 1
        }
        page_data = site.api(**ll_params)["query"]["pages"]
        page = next(iter(page_data.values()))
        has_en = "langlinks" in page and page["langlinks"]

        if not has_en:
            p = site.pages[subcat_full]
            text = p.text()
            tag_line = f"[[Category:{TAG_CAT}]]"
            if tag_line not in text:
                new_text = text.rstrip() + "\n" + tag_line + "\n"
                try:
                    p.save(new_text, summary=f"Bot: tag missing enwiki interwiki")
                    print(f"  • tagged {subcat_full}")
                except APIError as e:
                    print(f"  ! failed to tag {subcat_full}: {e.code}")
                time.sleep(THROTTLE)
            else:
                print(f"  • already tagged {subcat_full}")
        else:
            print(f"  • has en interwiki; skipping")
        time.sleep(THROTTLE)

    print("Done.")

if __name__ == "__main__":
    main()
