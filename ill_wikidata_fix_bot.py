#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py
=======================
Replaces {{ill|…}} on Shinto Wiki pages with enwiki links via Wikidata,
correctly handling both numbered parameters and bare titles.

Reads page titles from pages.txt, one per line.
"""

import os, sys
import re
import time
import requests
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0  # seconds between pages

ILL_RE = re.compile(r'\{\{\s*ill\|(.+?)\}\}', re.DOTALL)

# ─── WIKIDATA & WIKIPEDIA HELPERS ──────────────────────────────────
def get_wikidata_qid(ja_title: str) -> str | None:
    params = {
        "action": "wbgetentities",
        "format": "json",
        "sites": "jawiki",
        "titles": ja_title,
    }
    r = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=10)
    data = r.json().get("entities", {})
    for ent in data.values():
        qid = ent.get("id")
        if qid and qid.startswith("Q"):
            return qid
    return None

def get_enwiki_title(qid: str) -> str | None:
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": qid,
        "props": "sitelinks",
        "sitefilter": "enwiki",
    }
    r = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=10)
    ent = r.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl.get("title") if sl else None

def enwiki_is_redirect(title: str) -> bool:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "info",
    }
    r = requests.get("https://en.wikipedia.org/w/api.php", params=params, timeout=10)
    pages = r.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    return page.get("redirect", False)

# ─── PARAMETER PARSING ─────────────────────────────────────────────
def choose_label(parts: list[str]) -> str:
    # first collect bare parts (no '=')
    bare = [p for p in parts if '=' not in p]
    default_title = bare[0] if bare else parts[0].split('=',1)[-1]

    # last lt=
    lts = [p.split('=',1)[1] for p in parts if p.startswith("lt=")]
    if lts:
        return lts[-1]

    # last 1=
    ones = [p.split('=',1)[1] for p in parts if p.startswith("1=")]
    if ones:
        return ones[-1]

    return default_title

# ─── TEMPLATE REPLACEMENT ──────────────────────────────────────────
def repl(match):
    raw = match.group(0)
    inner = match.group(1)
    parts = [p.strip() for p in inner.split("|")]
    print(f"  ▶ found {{ill|…}} → {raw}")

    # find last 'ja' parameter index
    ja_idxs = [i for i,p in enumerate(parts) if p.startswith("ja=") or p=="ja"]
    if not ja_idxs:
        print("    ! no ja= param, skipping")
        return raw
    idx = ja_idxs[-1]
    # the title is either the value after 'ja=' or the next bare
    if parts[idx].startswith("ja="):
        ja_title = parts[idx].split("=",1)[1]
    elif idx+1 < len(parts):
        ja_title = parts[idx+1]
    else:
        print("    ! malformed ja:, skipping")
        return raw

    print(f"    → ja: {ja_title}")
    qid = get_wikidata_qid(ja_title)
    if not qid:
        print(f"    ! no Q-ID for '{ja_title}', skipping")
        return raw

    en_title = get_enwiki_title(qid)
    if not en_title:
        print(f"    ! no enwiki link for Q-ID {qid}, skipping")
        return raw

    if enwiki_is_redirect(en_title):
        print(f"    ! enwiki:{en_title} is a redirect, skipping")
        return raw

    label = choose_label(parts)
    replacement = f"[[:en:{en_title}|{label}]]"
    print(f"    ✓ replace with {replacement}")
    return replacement

# ─── MAIN LOOP ────────────────────────────────────────────────────
def load_pages():
    if not os.path.exists(PAGES_FILE):
        open(PAGES_FILE, "w", encoding="utf-8").close()
        print(f"Created empty {PAGES_FILE}. Fill it and re-run.")
        sys.exit(0)
    with open(PAGES_FILE, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    pages = load_pages()
    for i, title in enumerate(pages, 1):
        page = site.pages[title]
        if page.redirect:
            print(f"{i}/{len(pages)}: [[{title}]] is a redirect, skipping\n")
            continue

        print(f"{i}/{len(pages)}: [[{title}]]")
        text = page.text()
        new = ILL_RE.sub(repl, text)
        if new != text:
            try:
                page.save(new, summary="Bot: replace {{ill}} with enwiki links via Wikidata")
                print("    → saved.\n")
            except APIError as e:
                print(f"    ! save failed: {e}\n")
        else:
            print("    (no changes)\n")
        time.sleep(THROTTLE)

    print("Done.")

if __name__ == "__main__":
    main()
