#!/usr/bin/env python3
"""
ill_to_enwiki_cleanup.py
========================
Replace local links / {{ill|…}} templates with explicit en-wiki interwikis,
then delete the local page if nothing else links to it.

pages.txt  – list of *local* page titles to process (one per line).

Run with an optional first-title argument to resume a stopped run:
    python ill_to_enwiki_cleanup.py "Hya"
"""

# ─── EDIT ME ───────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
PAGES_TXT = "pages.txt"
THROTTLE  = 0.4          # seconds between edits
# ───────────────────────────────────────────────────────────────────

import re, sys, time, urllib.parse, datetime as dt, requests, os, pathlib
import mwclient
from mwclient.errors import APIError, InvalidPageTitle

EN_API = "https://en.wikipedia.org/w/api.php"
UA     = {"User-Agent": "ill-to-enwiki-clean/1.0 (User:Immanuelle)"}

START_AT = sys.argv[1] if len(sys.argv) > 1 else None

# ─── helpers: English-wiki existence check ─────────────────────────
def enwiki_exists(title: str) -> bool:
    """True if *title* exists on enwiki (case-insensitive)."""
    if not title or title.endswith(":"):
        return False
    try:
        r = requests.get(
            EN_API,
            params={"action":"query","titles":title,"format":"json"},
            headers=UA, timeout=8
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages")
        if not pages:
            return False
        pg = next(iter(pages.values()))
        return "missing" not in pg
    except Exception as err:
        print("  ! enwiki_exists API problem:", err, "- treat as missing")
        return False

# ─── mwclient convenience ──────────────────────────────────────────
def wiki_site():
    parsed = urllib.parse.urlparse(API_URL)
    return mwclient.Site(parsed.netloc,
                         path=parsed.path.rsplit("/api.php",1)[0] + "/")

def safe_page(site, title):
    try:
        return site.pages[title]
    except (InvalidPageTitle, KeyError, APIError):
        print("  ! invalid title:", title)
        return None

# ─── link/ILL conversion helpers ───────────────────────────────────
def _fuzzy(title:str) -> str:                # spaces/underscores interchangeable
    parts=[re.escape(p) for p in title.replace("_"," ").split(" ") if p]
    return r"[ _\s]*".join(parts)

def convert_plain_links(txt, local_title, en_title):
    pat = re.compile(rf"\[\[\s*{_fuzzy(local_title)}(\s*\|[^\]]+)?\]\]", re.I)
    def repl(m):
        tail = m.group(1) or f"|{en_title}"
        return f"[[:en:{en_title}{tail}]]"
    return pat.sub(repl, txt)

ILL_RX = re.compile(r"\{\{\s*ill\s*\|", re.I)

def convert_ill_templates(txt, local_title, en_title):
    """Replace every {{ill|local_title|ja|…}} with an enwiki link."""
    def replace_one(m):
        start = m.start()
        # find the matching closing '}}' (rudimentary, good enough for templates)
        depth = 2; i = m.end()
        while i < len(txt) and depth:
            if txt[i:i+2] == '{{': depth += 2; i += 2
            elif txt[i:i+2] == '}}': depth -= 2; i += 2
            else: i += 1
        chunk = txt[m.start():i]
        parts = [p.strip() for p in chunk[2:-2].split("|")]  # drop '{{' '}}'
        if not parts or parts[0].lower() != "ill":
            return chunk                 # shouldn't happen
        if len(parts) < 3:               # need at least param0, lang, param2
            return chunk
        if parts[0].lower() == "ill" and \
           parts[1].replace("_"," ") .casefold() == local_title.casefold():
            # determine link text
            label = parts[1]                             # default
            for p in parts[3:]:
                if p.lower().startswith("lt="):
                    label = p.split("=",1)[1].strip()
                    break
            return f"[[:en:{en_title}|{label}]]"
        return chunk

    out, pos = [], 0
    for m in ILL_RX.finditer(txt):
        out.append(txt[pos:m.start()])
        out.append(replace_one(m))
        # advance pos to end of consumed template
        close = txt.find("}}", m.end())
        pos = close+2 if close!=-1 else m.end()
    out.append(txt[pos:])
    return "".join(out)

def convert_links(text, local_title, en_title):
    text = convert_plain_links(text, local_title, en_title)
    text = convert_ill_templates(text, local_title, en_title)
    return text

# ─── main processing ───────────────────────────────────────────────
def load_titles() -> list[str]:
    with open(PAGES_TXT, encoding="utf8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]

def fix_backlinks(site, local_title, en_title):
    changed = 0
    blq = {"action":"query","list":"backlinks","bltitle":local_title,
           "blfilterredir":"nonredirects","bllimit":"max","format":"json"}
    data=site.api(**blq)
    for bl in data["query"]["backlinks"]:
        pg = safe_page(site, bl["title"])
        if not pg: continue
        txt = pg.text()
        new = convert_links(txt, local_title, en_title)
        if new != txt:
            try:
                pg.save(new,
                        summary="Bot: convert local/ILL link → enwiki interwiki")
                print("    •", pg.name)
                changed += 1
            except APIError as e:
                print("    ! save failed on", pg.name, e.code)
            time.sleep(THROTTLE)
    return changed

def main():
    if not os.path.exists(PAGES_TXT):
        raise SystemExit("pages.txt not found")

    site = wiki_site()
    site.login(USERNAME, PASSWORD)

    titles = load_titles()
    resume = bool(START_AT)
    for t in titles:
        if resume and t < START_AT:
            continue
        resume = False

        pg = safe_page(site, t)
        if not pg or not pg.exists:
            continue

        print(f"\n→ {t}")
        if not enwiki_exists(t):
            print("  • no enwiki page – skipped")
            continue

        # fix backlinks first
        fix_backlinks(site, t, t)

        # delete page if it still exists
        try:
            pg.delete(reason="Bot: exists on enwiki – replaced by interwiki",
                      watch=False)
            print("  • local page deleted")
        except APIError as e:
            print("  ! delete failed", e.code)
        time.sleep(THROTTLE)

    print("\nDone.")

# ─── run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
