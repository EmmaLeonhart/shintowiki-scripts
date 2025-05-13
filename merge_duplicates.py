"""
merge_duplicate_translations_bot.py
===================================

For each jawiki backlink page title in pages.txt:
 1. Load the page (which should list exactly two local pages as numbered links: `# [[PageA]]`, `# [[PageB]]`).
 2. If exactly two, treat the first as primary, second as duplicate.
 3. Fetch both pages' content from Shinto wiki.
 4. Append the duplicate's content under a heading "==Merged second translation==" to the primary.
 5. Add [[Category:Merged pages]] to the end of the merged content.
 6. Save the primary page with a summary noting the merge from the duplicate and reason.
 7. Replace the duplicate page with a redirect to the primary (no other content).

Usage:
  - List jawiki target page titles (the ones whose backlink pages you generated) in pages.txt
  - Configure credentials below
  - Run: python merge_duplicate_translations_bot.py
"""
import os
import sys
import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE   = 'pages.txt'      # list of backlink pages to process
WIKI_HOST    = 'shinto.miraheze.org'
WIKI_PATH    = '/w/'
USERNAME     = 'Immanuelle'
PASSWORD     = '[REDACTED_SECRET_1]'
THROTTLE     = 1.0              # seconds between operations

# ─── UTILITIES ────────────────────────────────────────────────────
def load_pages(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    pages = load_pages(PAGES_FILE)
    site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # regex to extract numbered backlinks: lines like '# [[PageName]]'
    BACKLINK_RE = re.compile(r'^# \[\[([^\]]+)\]\]', re.MULTILINE)

    for title in pages:
        print(f"Processing backlink list [[{title}]]...")
        page = site.pages[title]
        try:
            text = page.text()
        except Exception as e:
            print(f"  ! Failed to fetch [[{title}]]: {e}")
            continue

        matches = BACKLINK_RE.findall(text)
        if len(matches) != 2:
            print(f"  – Expected 2 backlinks, found {len(matches)}; skipping.")
            continue

        primary_name, duplicate_name = matches
        primary_page   = site.pages[primary_name]
        duplicate_page = site.pages[duplicate_name]

        # fetch contents
        try:
            primary_text = primary_page.text()
        except Exception as e:
            print(f"  ! Could not load [[{primary_name}]]: {e}")
            continue
        try:
            dup_text = duplicate_page.text()
        except Exception as e:
            print(f"  ! Could not load [[{duplicate_name}]]: {e}")
            dup_text = ''

        # build merged content
        merged = primary_text.rstrip() + "\n\n==Merged second translation==\n" + dup_text.rstrip() + "\n\n[[Category:Merged pages]]\n"

        # save merged primary
        summary = (f"Bot: merge duplicate translation from [[{duplicate_name}]] into [[{primary_name}]]; "
                   "accidental double translation")
        try:
            primary_page.save(merged, summary=summary)
            print(f"  ✓ Merged into [[{primary_name}]]")
        except APIError as e:
            print(f"  ! APIError saving [[{primary_name}]]: {e.code}")
            continue
        except Exception as e:
            print(f"  ! Error saving [[{primary_name}]]: {e}")
            continue

        # blank & redirect the duplicate page
        redirect_text = f"#redirect [[{primary_name}]]\n"
        try:
            duplicate_page.save(redirect_text,
                                summary=f"Bot: redirect duplicated translation to [[{primary_name}]]")
            print(f"  ✓ Redirected [[{duplicate_name}]] → [[{primary_name}]]")
        except APIError as e:
            print(f"  ! APIError redirecting [[{duplicate_name}]]: {e.code}")
        except Exception as e:
            print(f"  ! Error redirecting [[{duplicate_name}]]: {e}")

        time.sleep(THROTTLE)

    print("All done.")

if __name__ == '__main__':
    main()
