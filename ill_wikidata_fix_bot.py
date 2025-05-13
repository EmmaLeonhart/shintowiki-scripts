#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py
=======================
Replaces {{ill|…}} on Shinto Wiki pages with enwiki links via Wikidata,
skipping any target that resolves to a redirect.

Usage:
  1. List your page titles (one per line) in pages.txt.
  2. Configure your USERNAME/PASSWORD below.
  3. python ill_wikidata_fix_bot.py
"""

import os, sys, time, re
import requests
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0  # seconds between page edits

ILL_RE = re.compile(r"\{\{\s*ill\|(.+?)\}\}", re.DOTALL)

# ─── WIKIDATA & WIKIPEDIA HELPERS ──────────────────────────────────
def get_wikidata_qid(ja_title: str) -> str | None:
    """Given a Japanese page title, return its Wikidata Q-ID (jawiki site)."""
    r = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "sites":  "jawiki",
        "titles": ja_title,
    }, timeout=10)
    data = r.json().get("entities", {})
    for ent in data.values():
        qid = ent.get("id")
        if qid and qid.startswith("Q"):
            return qid
    return None

def get_enwiki_title(qid: str) -> str | None:
    """Given a Q-ID, return its English-wiki sitelink title (or None)."""
    r = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "ids":    qid,
        "props":  "sitelinks",
        "sitefilter": "enwiki",
    }, timeout=10)
    ent = r.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl.get("title") if sl else None

def enwiki_is_redirect(title: str) -> bool:
    """Returns True if the given enwiki title is itself a redirect."""
    r = requests.get("https://en.wikipedia.org/w/api.php", {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop":   "info",
    }, timeout=10)
    pages = r.json().get("query", {}).get("pages", {})
    pg = next(iter(pages.values()), {})
    return "redirect" in pg

# ─── PARAMETER PARSING ─────────────────────────────────────────────
def choose_label(parts: list[str]) -> str:
    """
    From the list of parts inside {{ill|…}}, choose the visible link label:
      1. Last lt=... if present
      2. Else last 1=... if present
      3. Else the first bare part (no '=').
    """
    lts = [p.split("=",1)[1] for p in parts if p.startswith("lt=")]
    if lts:
        return lts[-1].strip()

    ones = [p.split("=",1)[1] for p in parts if p.startswith("1=")]
    if ones:
        return ones[-1].strip()

    # bare parts = those with no '=' at all
    bare = [p for p in parts if "=" not in p]
    return bare[0].strip() if bare else parts[0].split("=",1)[-1].strip()

# ─── TEMPLATE REPLACEMENT ──────────────────────────────────────────
def repl(match):
    raw = match.group(0)
    inner = match.group(1)
    parts = [p.strip() for p in inner.split("|")]

    print(f"  ▶ found {{ill|…}} → {raw}")

    # locate last 'ja' parameter
    ja_idxs = [i for i,p in enumerate(parts)
               if p == "ja" or p.startswith("ja=")]
    if not ja_idxs:
        print("    ! no ja=, skipping")
        return raw

    idx = ja_idxs[-1]
    if parts[idx] == "ja":
        if idx+1 >= len(parts):
            print("    ! 'ja' at end, skipping")
            return raw
        ja_title = parts[idx+1]
    else:
        ja_title = parts[idx].split("=",1)[1]
    ja_title = ja_title.strip()
    print(f"    → ja: {ja_title}")

    # Wikidata Q-ID
    qid = get_wikidata_qid(ja_title)
    if not qid:
        print(f"    ! no Q-ID for '{ja_title}', skipping")
        return raw
    print(f"    → Q-ID: {qid}")

    # English title
    en_title = get_enwiki_title(qid)
    if not en_title:
        print(f"    ! no enwiki sitelink, skipping")
        return raw
    if enwiki_is_redirect(en_title):
        print(f"    ! enwiki:{en_title} is a redirect, skipping")
        return raw
    print(f"    → en: {en_title}")

    # choose human label
    label = choose_label(parts)
    replacement = f"[[:en:{en_title}|{label}]]"
    print(f"    ✓ replace with {replacement}")
    return replacement

# ─── MAIN LOOP ────────────────────────────────────────────────────
def load_pages():
    if not os.path.exists(PAGES_FILE):
        open(PAGES_FILE, "w", encoding="utf-8").close()
        print(f"Created empty {PAGES_FILE}; fill it and re-run.")
        sys.exit(0)
    with open(PAGES_FILE, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh
                if ln.strip() and not ln.startswith("#")]

def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    pages = load_pages()
    for idx, title in enumerate(pages, 1):
        page = site.pages[title]
        if page.redirect:
            print(f"{idx}/{len(pages)}: [[{title}]] is a redirect → skipping\n")
            continue

        print(f"{idx}/{len(pages)}: [[{title}]]")
        text = page.text()
        new  = ILL_RE.sub(repl, text)
        if new != text:
            try:
                page.save(new,
                          summary="Bot: replace {{ill}} with enwiki links via Wikidata")
                print("    → saved.\n")
            except APIError as e:
                print(f"    ! save failed: {e}\n")
        else:
            print("    (no changes)\n")

        time.sleep(THROTTLE)

    print("All done.")

if __name__ == "__main__":
    main()
