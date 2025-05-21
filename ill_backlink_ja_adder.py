#!/usr/bin/env python3
"""
ill_backlink_ja_adder.py
========================
For each title in **pages.txt**:

1. Look at every page that links to it (backlinks).
2. When a backlink contains an {{ill}} template that points to the target
   page, extract the Japanese title (either positional or `ja=` parameter).
3. If the target page lacks an explicit JA interwiki, append one
   (`[[ja:…]]`) using the *first* Japanese title discovered.

Run:
    python ill_backlink_ja_adder.py
"""

# ── CONFIG ──────────────────────────────────────────────────────────
SITE_URL   = "shinto.miraheze.org"
SITE_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"
THROTTLE   = 0.4          # seconds between edits

# ── imports ────────────────────────────────────────────────────────
import os, re, time, urllib.parse
import mwclient
from mwclient.errors import APIError

# ── regexes ────────────────────────────────────────────────────────
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]+?)\}\}", re.I | re.S)

def parse_ill(raw: str):
    """
    Return dict with keys:
        'en'  – the first positional parameter (page on this wiki)
        'ja'  – japanese title if present (positional or named)
    """
    parts = [p.strip() for p in raw.split("|")]
    pos   = []
    named = {}
    for p in parts:
        if "=" in p:
            k,v = p.split("=",1);  named[k.strip()] = v.strip()
        else:
            pos.append(p)

    en = pos[0] if pos else named.get("en")
    ja = (named.get("ja") or
          (pos[2] if len(pos) >= 3 and (pos[1].lower() == "ja") else None))
    if en:  en = urllib.parse.unquote(en).replace("_"," ").strip()
    if ja:  ja = urllib.parse.unquote(ja).replace("_"," ").strip()
    return {"en":en, "ja":ja}

# ── helpers ────────────────────────────────────────────────────────
def load_targets():
    if not os.path.exists(PAGES_FILE):
        raise SystemExit("Missing pages.txt")
    with open(PAGES_FILE, encoding="utf8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

def first_backlink_ja(site, target_title):
    """
    Scan backlinks until we find a JA title via {{ill}} that refers
    to *target_title*; return that JA string or None.
    """
    bl_continue = None
    while True:
        query = {
            "action":"query","list":"backlinks","bltitle":target_title,
            "blfilterredir":"nonredirects","bllimit":"max","format":"json"
        }
        if bl_continue:
            query["blcontinue"] = bl_continue
        data = site.api(**query)
        for bl in data["query"]["backlinks"]:
            pg = site.pages[bl["title"]]
            try:
                txt = pg.text()
            except Exception:
                continue
            for m in ILL_RE.finditer(txt):
                info = parse_ill(m.group(1))
                if (info.get("en") or "").strip() == target_title and info.get("ja"):
                    return info["ja"]
        if "continue" in data:
            bl_continue = data["continue"]["blcontinue"]
        else:
            break
    return None

# ── MAIN ───────────────────────────────────────────────────────────
def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    targets = load_targets()
    for num, title in enumerate(targets, 1):
        print(f"{num}/{len(targets)} – {title}")
        page = site.pages[title]
        if not page.exists:
            print("   ! page missing – skip"); continue

        if re.search(r"\n\[\[\s*ja:", page.text(), re.I):
            print("   • already has ja interwiki"); continue

        ja_title = first_backlink_ja(site, title)
        if not ja_title:
            print("   • no backlink with ja title found"); continue

        new_txt = page.text().rstrip() + f"\n[[ja:{ja_title}]]\n"
        try:
            page.save(new_txt,
                      summary=f"Bot: add ja interwiki from backlink ILL template")
            print(f"   ✓ added [[ja:{ja_title}]]")
        except APIError as e:
            print("   ! save failed:", e.code)
        time.sleep(THROTTLE)

    print("Done.")

if __name__ == "__main__":
    main()
