"""
create_week_redirects_evolutionism.py
=====================================
Creates Week/1 through Week/7 redirects to days of the week on evolutionism.miraheze.org.
Each redirect includes [[Category:order.life redirects]].
"""

import mwclient
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKI_URL = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.5  # seconds between edits

# Week/N -> Day of the week
REDIRECTS = {
    'Week/1': 'Monday',
    'Week/2': 'Tuesday',
    'Week/3': 'Wednesday',
    'Week/4': 'Thursday',
    'Week/5': 'Friday',
    'Week/6': 'Saturday',
    'Week/7': 'Sunday',
}

def main():
    print(f"Total redirects to create: {len(REDIRECTS)}\n")

    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    success = 0
    failed = 0
    skipped = 0

    for i, (source, target) in enumerate(REDIRECTS.items(), 1):
        print(f"[{i}/{len(REDIRECTS)}] {source} -> {target}", end=" ... ", flush=True)

        content = f"#REDIRECT [[{target}]]\n[[Category:order.life redirects]]"

        try:
            page = site.pages[source]
            if page.exists:
                print("SKIPPED (already exists)")
                skipped += 1
            else:
                page.save(content, summary=f"Bot: Create redirect to [[{target}]]")
                print("OK")
                success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        time.sleep(SLEEP)

    print(f"\n{'='*50}")
    print(f"Summary: {success} created, {skipped} skipped, {failed} failed out of {len(REDIRECTS)}")

if __name__ == "__main__":
    main()
