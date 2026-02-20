"""jawiki_full_import_bot.py
===========================
Import **full history** for every Japanese‑Wikipedia page listed in
*pages.txt* directly into your shinto.miraheze.org wiki.

How it works
------------
* Reads each line of *pages.txt* (ignores blank lines / comments).
* Tries **transwiki import** first (`interwikisource="jawiki"`).
* If the wiki doesn’t recognise that source (API error `badvalue`),
  falls back to **XML export + multipart upload** — still full history.
* Creates the page automatically if it doesn’t exist locally.

No merging, no templates, no edits to existing pages — this script is
solely to prove that full‑history import works.

Prerequisites
-------------
* Account must have **`import`** and (for the fallback) **`importupload`**.
* `pip install mwclient requests` if not already installed.
"""

import os
import sys
import time
import re
import requests
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"   # domain only
WIKI_PATH = "/w/"                  # include leading & trailing slashes
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
PAGES_TXT = "pages.txt"            # each line = ja‑wiki page title
THROTTLE  = 1.0                    # seconds between imports

API_URL = f"https://{WIKI_URL}{WIKI_PATH}api.php"

# ─── SESSION ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print("Logged in.")

# ─── FILE HELPERS ─────────────────────────────────────────────────

def ensure_pagelist() -> list[str]:
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT, "w", encoding="utf-8").close()
        print(f"Created empty {PAGES_TXT}; add ja‑wiki titles and run again.")
        sys.exit()
    with open(PAGES_TXT, "r", encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

# ─── JAPAN WIKI HELPERS ───────────────────────────────────────────

def fetch_export_xml(ja_title: str) -> bytes:
    """Download full history XML via Special:Export (always includes history)."""
    import urllib.parse
    url = (
        "https://ja.wikipedia.org/wiki/Special:Export/" +
        urllib.parse.quote(ja_title, safe="")
    )
    params = {"history": "1", "templates": "1"}
    r = requests.get(url, params=params, timeout=90)
    r.raise_for_status()
    return r.content

# ─── IMPORT ROUTINES ───────────────────────────────────────────────

def import_transwiki(ja_title: str, token: str) -> bool:
    try:
        site.api(
            "import", token=token,
            interwikisource="jawiki",
            interwikipage=ja_title,
            fullhistory=1,
            summary=f"Bot: import full history from ja:{ja_title}",
        )
        return True
    except APIError as e:
        if e.code == "badvalue":
            return False  # jawiki not registered
        print(f"   ! transwiki import failed – {e}")
        return False


def import_xml_upload(xml_bytes: bytes, ja_title: str, token: str) -> bool:
    data = {
        "action": "import", "format": "json", "token": token,
        "interwikiprefix": "ja", "assignknownusers": "1",
        "summary": f"Bot: import full history from ja:{ja_title}",
    }
    files = {"xml": ("history.xml", xml_bytes, "text/xml")}
    res = site.connection.post(API_URL, data=data, files=files, timeout=90).json()
    if res.get("error"):
        print(f"   ! xml upload failed – {res['error']['info']}")
        return False
    return True

# ─── MAIN DRIVER ──────────────────────────────────────────────────

def process_title(ja_title: str) -> None:
    token = site.get_token("csrf")

    # First try transwiki import
    if import_transwiki(ja_title, token):
        print(f"   • imported via transwiki → [[{ja_title}]]")
        return

    # Fallback: XML upload
    try:
        xml_bytes = fetch_export_xml(ja_title)
    except Exception as e:
        print(f"   ! export failed – {e}")
        return

    if import_xml_upload(xml_bytes, ja_title, token):
        print(f"   • imported via XML upload → [[{ja_title}]]")

# ─── MAIN LOOP ────────────────────────────────────────────────────

def main() -> None:
    titles = ensure_pagelist()
    if not titles:
        print("pages.txt is empty – nothing to import.")
        return

    for i, ja_title in enumerate(titles, 1):
        print(f"{i}/{len(titles)} ja:{ja_title}")
        process_title(ja_title)
        time.sleep(THROTTLE)

    print("Done!")


if __name__ == "__main__":
    main()
