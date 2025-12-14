"""
jawiki_backlinks_bot.py
======================
For each page title in pages.txt:
 1. Fetch the first [[ja:XXX]] interwiki link in the page text.
 2. For that XXX, fetch or create a page named XXX on Shinto Wiki.
 3. If the page is new, initialize with:
      # [[LocalPage]]
      [[Category:jawiki 1 backlink]]
    If it exists, append a new line:
      # [[LocalPage]]
    Then update its category to:
      [[Category:jawiki N backlink(s)]]
    where N is the updated total, using singular 'backlink' when N==1, else 'backlinks'.

Usage:
  - List local pages in pages.txt
  - Configure credentials below
  - Run: python jawiki_backlinks_bot.py
"""
import os
import sys
import re
import time
import urllib.parse
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE  = 'pages.txt'      # list of local page titles
WIKI_HOST   = 'shinto.miraheze.org'
WIKI_PATH   = '/w/'
USERNAME    = 'Immanuelle'
PASSWORD    = '[REDACTED_SECRET_1]'
THROTTLE    = 1.0              # seconds between edits

# ─── LOAD LOCAL TITLES ────────────────────────────────────────────
def load_pages(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add page titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    pages = load_pages(PAGES_FILE)
    site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    JA_RE = re.compile(r"\[\[\s*ja:([^\]|]+)")
    CAT_RE = re.compile(r"\[\[Category:jawiki (\d+) backlink(?:s)?\]\]")

    for title in pages:
        print(f"Processing local [[{title}]]...")
        try:
            text = site.pages[title].text()
        except Exception as e:
            print(f"  ! Could not fetch [[{title}]]: {e}")
            continue
        m = JA_RE.search(text)
        if not m:
            print("  – No ja: link; skipping.")
            continue
        raw = m.group(1).strip()
        ja_title = urllib.parse.unquote(raw).replace('_', ' ')
        print(f"  → ja:{ja_title}")

        target = site.pages[ja_title]
        try:
            existing = target.text()
        except Exception:
            existing = ''
        # split out existing lines, remove old jawiki category
        lines = existing.splitlines()
        new_lines = [l for l in lines if not CAT_RE.match(l)]
        # remove duplicate backlink entry if exists
        backlink_line = f"# [[{title}]]"
        if backlink_line in new_lines:
            print(f"  – [[{title}]] already listed; skipping backlink addition.")
        else:
            new_lines.append(backlink_line)

        # count backlinks = number of lines starting with '# ['
        count = sum(1 for l in new_lines if l.startswith('# ['))
        suffix = 'backlink' if count == 1 else 'backlinks'
        cat_line = f"[[Category:jawiki {count} {suffix}]]"
        # remove any old category lines
        new_lines = [l for l in new_lines if not CAT_RE.match(l)]
        # ensure blank line before category
        if new_lines and new_lines[-1].strip() != '':
            new_lines.append('')
        new_lines.append(cat_line)

        new_text = '\n'.join(new_lines) + '\n'
        if new_text.strip() != existing.strip():
            try:
                target.save(new_text, summary=f"Bot: add backlink [[{title}]] to ja:{ja_title}")
                print(f"  ✓ Updated [[{ja_title}]] (count={count})")
            except APIError as e:
                print(f"  ! APIError saving [[{ja_title}]]: {e.code}")
            except Exception as e:
                print(f"  ! Error saving [[{ja_title}]]: {e}")
        else:
            print(f"  – No change for [[{ja_title}]]")

        time.sleep(THROTTLE)

    print("Done.")

if __name__ == '__main__':
    main()
