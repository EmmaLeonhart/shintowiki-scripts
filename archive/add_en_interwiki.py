#!/usr/bin/env python3
"""
add_en_interwiki.py
===================
Reads **pages.txt** (one title per line). For each local page:
1. Checks if a page of the *same* title exists on English Wikipedia.
2. If yes **and** the local page does *not* already contain an
   `[[en:PAGENAME]]` interwiki, append that line at the very bottom.

Usage
-----
```bash
python add_en_interwiki.py
```
Edit the credentials/API URL block first.
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
EN_API   = "https://en.wikipedia.org/w/api.php"
# <<< credentials <<<

import os, sys, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

PAGES_FILE = "pages.txt"; THROTTLE = 0.4
UA = {"User-Agent": "en-interwiki-adder/1.0 (User:Immanuelle)"}

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# ─── enwiki exists? ───────────────────────────────────────────────

def enwiki_exists(title:str)->bool:
    r=requests.get(EN_API, params={"action":"query","titles":title,"format":"json"}, headers=UA, timeout=10)
    r.raise_for_status()
    pg=next(iter(r.json()["query"]["pages"].values()))
    return "missing" not in pg

# ─── main loop ────────────────────────────────────────────────────

def load_titles():
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    with open(PAGES_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def main():
    s=site(); print("Logged in")
    for t in load_titles():
        print("→", t)
        pg=s.pages[t]
        if not pg.exists:
            print("  ! local page missing – skip"); continue
        if not enwiki_exists(t):
            print("  • no enwiki page – skip"); continue
        iw_line=f"[[en:{t}]]"
        if iw_line in pg.text():
            print("  • interwiki already present")
            continue
        new=pg.text().rstrip()+"\n"+iw_line+"\n"
        try:
            pg.save(new, summary="Bot: add enwiki interwiki link")
            print("  ✓ added interwiki")
        except APIError as e:
            print("  ! save failed", e.code)
        time.sleep(THROTTLE)
    print("Done.")

if __name__=='__main__':
    main()