#!/usr/bin/env python3
"""
redirect_category_fixer.py  –  move members out of redirect categories (v1.1)
===========================================================================

* Reads **redirect_categories.txt** (one title per line).
* For each title that is a local **redirect** to another category:
  1. Finds the redirect target.
  2. Rewrites every member page so `[[Category:Old]]` (or with sort key)
     becomes `[[Category:Target]]`.
  3. Prints a per‑category summary:  “→ moved N pages from Old → Target”.
* Leaves the redirect category page itself intact.
"""
import os, re, time, urllib.parse, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL    = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME    = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
CAT_FILE    = "redirect_categories.txt"
THROTTLE    = 0.4

REDIR_RX = re.compile(r"#redirect\s*\[\[\s*:Category:([^\]]+)", re.I)

# ─── HELPERS ─────────────────────────────────────────────────────────

def norm(title: str) -> str:
    if title.lower().startswith("category:"):
        title = title[9:]
    return urllib.parse.unquote(title).replace('_', ' ').strip()


def load_titles():
    if not os.path.exists(CAT_FILE):
        raise SystemExit("Missing redirect_categories.txt")
    with open(CAT_FILE, encoding="utf-8") as fh:
        return [norm(l) for l in fh if l.strip() and not l.startswith('#')]


def members_of(site, cat_full):
    members = []
    cont = None
    while True:
        cm = {
            "action": "query",
            "list":   "categorymembers",
            "cmtitle": cat_full,
            "cmtype":  "page|subcat|file",
            "cmlimit": "max",
            "format": "json"
        }
        if cont:
            cm["cmcontinue"] = cont
        data = site.api(**cm)
        members.extend(m["title"] for m in data["query"]["categorymembers"])
        if "continue" in data:
            cont = data["continue"]["cmcontinue"]
        else:
            break
    return members



def swap_cat(page, old, new):
    txt = page.text()
    old_rx = re.escape(old).replace(r"\ ", "[ _]")
    pat = re.compile(rf"\[\[\s*Category:{old_rx}([^\]]*)\]\]", re.I)
    if not pat.search(txt):
        return False
    new_txt = pat.sub(lambda m: f"[[Category:{new}{m.group(1)}]]", txt)
    if new_txt == txt:
        return False
    try:
        page.save(new_txt, summary=f"Bot: move category {old} → {new}", minor=True)
        return True
    except APIError:
        return False

# ─── MAIN ───────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    for cat in load_titles():
        full = f"Category:{cat}"
        pg = site.pages[full]
        print("→", cat)
        if not (pg.exists and pg.redirect):
            print("  • not a redirect – skipped"); continue
        m = REDIR_RX.match(pg.text())
        if not m:
            print("  • cannot parse redirect – skipped"); continue
        target = norm(m.group(1))
        print("  • target:", target)

        moved = 0
        for title in members_of(site, full):
            if swap_cat(site.pages[title], cat, target):
                moved += 1
                print("    •", title)
                time.sleep(THROTTLE)
        print(f"  → moved {moved} pages from {cat} → {target}")
    print("All redirect categories processed.")

if __name__ == '__main__':
    main()
