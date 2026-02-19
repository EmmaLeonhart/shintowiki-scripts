#!/usr/bin/env python3
"""
tier1_enwiki_check_bot.py  (with resume support and full continuation)
==================================================================

Scans all subcategories of [[Category:Tier 1 Categories]] and tags those
without an English Wikipedia interwiki by adding them to
[[Category:Tier 1 Categories with no enwiki]]. Supports resuming after a
specific subcategory to complete a full run.

Usage:
  - Edit the RESUME_AFTER constant to the last processed subcategory title
    (including "Category:"). Leave as None to start from the beginning.

Steps:
1. Log in via mwclient.
2. Retrieve subcategories in batches using 'cmcontinue'.
3. Optionally skip until RESUME_AFTER is seen.
4. For each subcategory:
   a. Query for English langlink.
   b. If none, append [[Category:Tier 1 Categories with no enwiki]].
5. Throttle API calls and edits.
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
RESUME_AFTER = "Category:Squid in culture"

# ─── MAIN TASK ──────────────────────────────────────────────────────
def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}, scanning subcategories...")

    skipping = bool(RESUME_AFTER)
    if skipping:
        print(f"Resuming after: {RESUME_AFTER}")

    cmcontinue = None
    while True:
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{SOURCE_CAT}',
            'cmtype': 'subcat',
            'cmlimit': 'max',
            'format': 'json'
        }
        if cmcontinue:
            params['cmcontinue'] = cmcontinue

        data = site.api(**params)
        members = data.get('query', {}).get('categorymembers', [])

        for entry in members:
            subcat = entry['title']  # e.g. 'Category:Example'
            if skipping:
                if subcat == RESUME_AFTER:
                    skipping = False
                    print(f"Resumed at {subcat}, now processing subsequent categories...")
                continue

            print(f"Checking {subcat}")
            # Check English interwiki via langlinks
            ll = site.api(
                action='query', titles=subcat,
                prop='langlinks', lllang='en', lllimit='1', format='json'
            )
            page = next(iter(ll.get('query', {}).get('pages', {}).values()), {})
            has_en = bool(page.get('langlinks'))

            if not has_en:
                p = site.pages[subcat]
                text = p.text()
                tag = f'[[Category:{TAG_CAT}]]'
                if tag not in text:
                    new_text = text.rstrip() + "\n" + tag + "\n"
                    try:
                        p.save(new_text, summary='Bot: tag missing en interwiki')
                        print(f"  • tagged {subcat}")
                    except APIError as e:
                        print(f"  ! failed to tag {subcat}: {e.code}")
                    time.sleep(THROTTLE)
                else:
                    print(f"  • already tagged {subcat}")
            else:
                print(f"  • has en interwiki; skipping {subcat}")
            time.sleep(THROTTLE)

        # handle continuation
        cont = data.get('continue', {})
        cmcontinue = cont.get('cmcontinue')
        if not cmcontinue:
            break
        print(f"Fetching next batch with cmcontinue={cmcontinue}...")

    print("Done scanning all Tier 1 subcategories.")

if __name__ == '__main__':
    main()
