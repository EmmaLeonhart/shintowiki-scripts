#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py
=======================
Replaces {{ill|…}} templates on Shinto Wiki pages with
direct enwiki sitelinks (via Wikidata), handling numeric
and named parameters correctly (including “10=de → 11=…”)
and skipping any enwiki redirects.

Usage:
 1. Put one page title per line in pages.txt (comment lines with #).
 2. Configure USERNAME/PASSWORD below.
 3. Run: python ill_wikidata_fix_bot.py
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

# ─── HELPERS FOR WIKIDATA & REDIRECT CHECK ─────────────────────────
def get_wikidata_qid(de_title: str) -> str | None:
    resp = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "sites":  "dewiki",
        "titles": de_title,
    }, timeout=10)
    ents = resp.json().get("entities", {})
    for ent in ents.values():
        qid = ent.get("id")
        if qid and qid.startswith("Q"):
            return qid
    return None

def get_enwiki_title(qid: str) -> str | None:
    resp = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "ids":    qid,
        "props":  "sitelinks",
        "sitefilter": "enwiki",
    }, timeout=10)
    ent = resp.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl and sl.get("title")

def enwiki_is_redirect(title: str) -> bool:
    resp = requests.get("https://en.wikipedia.org/w/api.php", {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop":   "info",
    }, timeout=10)
    pages = resp.json().get("query", {}).get("pages", {})
    pg = next(iter(pages.values()), {})
    return "redirect" in pg

# ─── PARAMETER PARSING ─────────────────────────────────────────────
def parse_ill_params(inner: str):
    parts = [p.strip() for p in inner.split("|")]
    num   = {}
    named = {}
    # 1) collect all explicit assignments
    for p in parts:
        if "=" in p:
            key, val = p.split("=",1)
            key = key.strip(); val = val.strip()
            if key.isdigit():
                num[int(key)] = val
            else:
                named[key]    = val
    # 2) feed bare positional into next free numeric slots
    idx = 1
    for p in parts:
        if "=" in p:
            continue
        while idx in num:
            idx += 1
        num[idx] = p
        idx += 1
    return num, named, parts

def choose_label(num, named):
    if "lt" in named and named["lt"].strip():
        return named["lt"].strip()
    return num.get(1, "").strip()

def find_dewiki_title(num, named, parts):
    # 1) named `de=…` wins
    if "de" in named and named["de"].strip():
        return named["de"].strip()

    dewikis = []
    # 2) numeric slot whose value == 'de' → next slot
    for n in sorted(num):
        if num[n] == "de" and (n+1) in num and num[n+1].strip():
            dewikis.append(num[n+1].strip())

    # 3) fallback: bare 'de' in parts → next part
    for i,p in enumerate(parts):
        if p == "de" and i+1 < len(parts):
            dewikis.append(parts[i+1].strip())

    return dewikis[-1] if dewikis else None

# ─── TEMPLATE REPLACEMENT ──────────────────────────────────────────
def repl(match):
    raw   = match.group(0)
    inner = match.group(1)
    num, named, parts = parse_ill_params(inner)

    print(f"  ▶ Found {{ill|…}}: {raw}")
    de = find_dewiki_title(num, named, parts)
    if not de:
        print("    ! no de= found; skipping")
        return raw
    print(f"    → de: {de}")

    qid = get_wikidata_qid(de)
    if not qid:
        print("    ! no QID; skipping")
        return raw
    print(f"    → QID: {qid}")

    en = get_enwiki_title(qid)
    if not en:
        print("    ! no enwiki link; skipping")
        return raw
    if enwiki_is_redirect(en):
        print(f"    ! enwiki:{en} is a redirect; skipping")
        return raw
    print(f"    → en: {en}")

    label = choose_label(num, named)
    if not label:
        print("    ! no label; skipping")
        return raw

    replacement = f"[[:en:{en}|{label}]]"
    print(f"    ✓ Replacing with {replacement}")
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
    for idx, title in enumerate(pages, 1):
        print(f"{idx}/{len(pages)}: [[{title}]]")
        page = site.pages[title]
        if page.redirect:
            print("  ↳ Redirect; skipping\n")
            continue

        text = page.text()
        new  = ILL_RE.sub(repl, text)

        if new != text:
            try:
                page.save(new,
                          summary="Bot: replace {{ill}} with enwiki link via Wikidata")
                print("  → Page saved.\n")
            except APIError as e:
                print(f"  ! Save failed: {e}\n")
        else:
            print("  (no change)\n")

        time.sleep(THROTTLE)

    print("All done.")

if __name__ == "__main__":
    main()
