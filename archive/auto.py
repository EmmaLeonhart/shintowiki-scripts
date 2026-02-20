"""
auto_redirect_bot.py

Reads page titles from pages.txt (one per line) and, for each title that
*does not* yet exist on shinto.miraheze.org, creates an automatic redirect to
enwiki with the category [[Category:automatic wikipedia redirects]].
"""
import os
import time
import mwclient

# ─── Configuration ─────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
PAGES_FILE = 'pages.txt'

# ─── Connect & Login ───────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# ─── Main Logic ────────────────────────────────────────────────
def main():
    # Ensure pages.txt exists
    if not os.path.exists(PAGES_FILE):
        with open(PAGES_FILE, 'w', encoding='utf-8'):
            pass
        print(f"Created empty {PAGES_FILE}. Add page titles (one per line) and re-run.")
        return

    # Read titles
    with open(PAGES_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        titles = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Process each title
    for idx, title in enumerate(titles, 1):
        page = site.pages[title]
        if page.exists:
            print(f"{idx}/{len(titles)} [[{title}]] already exists – skipped")
        else:
            redirect_text = (
                f"#redirect[[:en:{title}]]\n"
                "[[Category:automatic wikipedia redirects]]"
            )
            try:
                page.save(redirect_text, summary="Bot: create automatic enwiki redirect")
                print(f"{idx}/{len(titles)} [[{title}]] redirect created")
            except Exception as e:
                print(f"{idx}/{len(titles)} [[{title}]] ERROR: {e}")
            time.sleep(1)

if __name__ == '__main__':
    main()
