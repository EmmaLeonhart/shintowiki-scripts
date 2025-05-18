#!/usr/bin/env python3
"""
enwiki_redirect_cleanup.py
==========================

Traverses **all main‑namespace pages** on the local wiki that are pure
redirects to English Wikipedia pages, fixes local backlinks into explicit
`[[:en:…]]` interwiki links, and deletes the redirect when no links remain.

Redirect patterns recognised (case‑insensitive, leading whitespace okay):
    #redirect [[en:Page]]
    #redirect [[:en:Page]]

Steps for each redirect page R (title T):
1. Extract target page name `Page`.
2. Query enwiki API – if target page is **missing** on enwiki, skip R.
3. Fetch backlinks to T (excluding redirects).
4. For each backlink page B:
   • Replace all `[[T]]` → `[[:en:Page|Page]]`.
   • Replace `[[T|text]]` → `[[:en:Page|text]]`.
   • Save if changed.
5. After processing, query backlinks again. If none remain → delete R.

Requires admin rights (page delete). Uses mwclient for local wiki and
requests for enwiki API.
"""
import re, time, sys, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL   = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME    = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE    = 0.5
EN_API      = "https://en.wikipedia.org/w/api.php"
UA          = {"User-Agent": "enwiki-redirect-clean/1.0 (User:Immanuelle)"}

REDIR_RE = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):([^\]|]+)", re.I)

# ─── HELPERS ───────────────────────────────────────────────────────

def enwiki_exists(title:str)->bool:
    r=requests.get(EN_API, params={"action":"query","titles":title,
                                   "format":"json"}, headers=UA, timeout=8)
    pg=next(iter(r.json()["query"]["pages"].values()))
    return "missing" not in pg


def fix_backlinks(site, local_title:str, en_title:str):
    changed=False
    bl_params={"action":"query","list":"backlinks","bltitle":local_title,
               "blfilterredir":"nonredirects","bllimit":"max","format":"json"}
    data=site.api(**bl_params)
    for bl in data["query"]["backlinks"]:
        pg=site.pages[bl["title"]]
        txt=pg.text()
        # replace [[Title]] and [[Title|text]]
        patt=re.compile(rf"\[\[\s*{re.escape(local_title)}(\s*\|[^\]]+)?\]\]",re.I)
        def repl(m):
            tail=m.group(1) or f"|{en_title}"
            return f"[[:en:{en_title}{tail}]]"
        new_txt=patt.sub(repl,txt)
        if new_txt!=txt:
            try:
                pg.save(new_txt, summary=f"Bot: convert local link → enwiki interwiki")
                print("    •", bl["title"])
                changed=True
            except APIError as e:
                print("    !", bl["title"], e.code)
            time.sleep(THROTTLE)
    return changed

# ─── MAIN ──────────────────────────────────────────────────────────

def main():
    site=mwclient.Site(LOCAL_URL,path=LOCAL_PATH)
    site.login(USERNAME,PASSWORD)

    # iterate all redirects in main ns (0)
    apc=None
    while True:
        ap={"action":"query","list":"allpages","apnamespace":0,
             "apfilterredir":"redirects","aplimit":"max","format":"json"}
        if apc: ap["apcontinue"]=apc
        data=site.api(**ap); pages=data["query"]["allpages"]
        for p in pages:
            title=p["title"]
            pg=site.pages[title]
            m=REDIR_RE.match(pg.text()) if pg.exists else None
            if not m:
                continue
            en_title=urllib.parse.unquote(m.group(1)).replace('_',' ')
            print("\n→", title, "-> enwiki:", en_title)
            if not enwiki_exists(en_title):
                print("  • enwiki page missing; skipped")
                continue
            # fix backlinks
            fix_backlinks(site, title, en_title)
            # check backlinks again
            bl=site.api(action='query',list='backlinks',bltitle=title,
                        blfilterredir='nonredirects',bllimit=1,format='json')
            if not bl['query']['backlinks']:
                try:
                    pg.delete(reason="Bot: remove obsolete enwiki redirect", watch=False)
                    print("  • redirect deleted (no backlinks)")
                except APIError as e:
                    print("  ! delete failed", e.code)
            time.sleep(THROTTLE)
        if 'continue' in data:
            apc=data['continue']['apcontinue']
        else:
            break
    print("Done.")

if __name__=='__main__':
    main()
