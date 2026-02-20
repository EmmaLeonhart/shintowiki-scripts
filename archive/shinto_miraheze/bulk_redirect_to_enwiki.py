#!/usr/bin/env python3
"""
bulk_redirect_to_enwiki.py
──────────────────────────
Read titles from pages.txt (one per line, blank- and #-comment lines ignored)
and overwrite / create each page with:

    #redirect[[en:{{subst:PAGENAME}}]]

Run:
    python bulk_redirect_to_enwiki.py
"""

import os, time, urllib.parse, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ───── CONFIG ──────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
PAGES_TXT = "pages.txt"
THROTTLE  = 0.4          # seconds between edits
# ------------------------------------------------------------------

REDIRECT_TEXT = "#redirect[[en:{{subst:PAGENAME}}]]\n"

def load_titles(path: str) -> list[str]:
    if not os.path.isfile(path):
        raise SystemExit(f"{path} not found")
    titles = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                titles.append(ln)
    return titles

def main() -> None:
    parsed = urllib.parse.urlparse(API_URL)
    site   = mwclient.Site(parsed.netloc, path=parsed.path.rsplit("/api.php",1)[0] + "/")
    site.login(USERNAME, PASSWORD)

    for n, title in enumerate(load_titles(PAGES_TXT), 1):
        print(f"{n:>3} • {title}")

        # attempt to get / create the page safely
        try:
            page = site.pages[title]
        except (InvalidPageTitle, KeyError):
            print("    ! invalid title – skipped");  continue

        try:
            page.save(REDIRECT_TEXT,
                      summary="Bot: redirect to enwiki page with same title",
                      minor=True, bot=True)
            print("    ✓ saved (redirect set)")
        except APIError as e:
            print("    ! save failed:", e.code)

        time.sleep(THROTTLE)

    print("All titles processed.")

if __name__ == "__main__":
    main()
