"""
remove_defaultsort_digits.py
============================
For every page in [[Category:Wikidata generated shikinaisha pages]],
remove any {{DEFAULTSORT:NNNNNNNN}} where the sort key is purely numeric
(i.e. a Wikidata QID number left in by the generator).
"""

import os
import mwclient
import re
import time
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
SLEEP = 1.5

CATEGORY = 'Wikidata generated shikinaisha pages'
# Matches any {{DEFAULTSORT:...}}
PATTERN = re.compile(r'\{\{DEFAULTSORT:[^}]*\}\}\n?', re.IGNORECASE)


def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (EmmaBot@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL}")

    cat = site.categories[CATEGORY]
    pages = list(cat)
    total = len(pages)
    print(f"Found {total} pages in Category:{CATEGORY}\n")

    done = 0
    skipped = 0
    errors = 0

    for i, page in enumerate(pages, 1):
        title = page.name
        print(f"[{i}/{total}] {title}")

        try:
            text = page.text()
            if not text:
                print("  SKIP (empty)")
                skipped += 1
                continue

            new_text, count = PATTERN.subn('', text)
            if count == 0:
                print("  SKIP (no numeric DEFAULTSORT)")
                skipped += 1
                continue

            page.save(new_text, summary=f"Bot: Removing numeric DEFAULTSORT (Wikidata QID artefact)")
            print(f"  SAVED: removed {count} DEFAULTSORT(s)")
            done += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

        time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"Done! Edited: {done}, Skipped: {skipped}, Errors: {errors}")
    print(f"Total pages: {total}")


if __name__ == "__main__":
    main()
