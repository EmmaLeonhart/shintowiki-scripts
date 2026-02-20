#!/usr/bin/env python3
"""
enwiki_redirect_cleanup.py  –  resume-able version
==================================================

Usage
-----
    python enwiki_redirect_cleanup.py            # full run
    python enwiki_redirect_cleanup.py "Ab"       # resume at first title ≥ “Ab”
"""
import re, time, sys, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle";         PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "enwiki-redirect-clean/1.1 (User:Immanuelle)"}

START_AT   = sys.argv[1] if len(sys.argv) > 1 else None   # optional resume point

REDIR_RE = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):([^\]|]+)", re.I)

# ─── HELPERS ───────────────────────────────────────────────────────
def enwiki_exists(title: str) -> bool:
    """
    Return True when *title* exists as a page on English Wikipedia
    (case-insensitive).

    The function is hardened so that **any** API irregularity – network
    error, bad response, or an unexpected JSON layout such as the one that
    raised `KeyError: 'pages'` – simply returns *False* instead of killing
    the whole run.
    """
    if not title or title.endswith(":"):         # empty / namespace prefix only
        return False

    try:
        r = requests.get(
            EN_API,
            params={
                "action": "query",
                "titles": title,
                "format": "json"
            },
            headers=UA,
            timeout=8
        )
        r.raise_for_status()
        data = r.json()

        # Some edge cases (e.g. malformed titles) return an 'error' field,
        # others return {"batchcomplete": …} without a 'pages' dict.
        pages = data.get("query", {}).get("pages")
        if not pages:                       # missing key → treat as nonexistent
            return False

        pg = next(iter(pages.values()))
        return "missing" not in pg

    except Exception as err:                # requests or json failure
        print("  ! enwiki_exists API problem:", err, "- treating as missing")
        return False



def fix_backlinks(site, local_title: str, en_title: str) -> bool:
    changed = False
    params = {"action":"query","list":"backlinks","bltitle":local_title,
              "blfilterredir":"nonredirects","bllimit":"max","format":"json"}
    for bl in site.api(**params)["query"]["backlinks"]:
        pg  = site.pages[bl["title"]]
        txt = pg.text()
        patt = re.compile(rf"\[\[\s*{re.escape(local_title)}(\s*\|[^\]]+)?\]\]", re.I)

        def repl(m):
            tail = m.group(1) or f"|{en_title}"
            return f"[[:en:{en_title}{tail}]]"

        new = patt.sub(repl, txt)
        if new != txt:
            try:
                pg.save(new, summary="Bot: convert local link → enwiki interwiki")
                print("    •", bl["title"])
                changed = True
            except APIError as e:
                print("    !", bl["title"], e.code)
            time.sleep(THROTTLE)
    return changed

# --- add near the other helpers -----------------------------------
from mwclient.errors import InvalidPageTitle

def safe_page(site, title):
    """Return mwclient.Page or None if API returned an error."""
    try:
        return site.pages[title]
    except (InvalidPageTitle, KeyError, APIError):
        print("  ! API failure on", title, "- skipped")
        return None
# ------------------------------------------------------------------


# ─── MAIN ──────────────────────────────────────────────────────────
def main():
    site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
    site.login(USERNAME, PASSWORD)

    apcontinue = None
    resume_flag = bool(START_AT)  # True until we pass start point

    while True:
        query = {"action":"query","list":"allpages","apnamespace":0,
                 "apfilterredir":"redirects","aplimit":"max","format":"json"}
        if apcontinue:
            query["apcontinue"] = apcontinue

        batch = site.api(**query)

        for entry in batch["query"]["allpages"]:
            title = entry["title"]

            # skip until we reach or pass the requested start title
            if resume_flag and title < START_AT:
                continue
            resume_flag = False   # we have now reached the starting point

            pg = safe_page(site, title)
            if not pg or not pg.exists:
                continue
            m = REDIR_RE.match(pg.text())

            if not m:
                continue

            en_title = urllib.parse.unquote(m.group(1)).replace('_', ' ')
            print(f"\n→ {title}  → enwiki: {en_title}")

            if not enwiki_exists(en_title):
                print("  • enwiki page missing; skipped")
                continue

            fix_backlinks(site, title, en_title)

            # if no backlinks remain, delete the redirect
            blck = site.api(action='query', list='backlinks', bltitle=title,
                            blfilterredir='nonredirects', bllimit=1,
                            format='json')['query']['backlinks']
            if not blck:
                try:
                    pg.delete(reason="Bot: remove obsolete enwiki redirect",
                              watch=False)
                    print("  • redirect deleted (no backlinks)")
                except APIError as e:
                    print("  ! delete failed", e.code)
            time.sleep(THROTTLE)

        if 'continue' in batch:
            apcontinue = batch['continue']['apcontinue']
        else:
            break

    print("Done.")

if __name__ == "__main__":
    main()
