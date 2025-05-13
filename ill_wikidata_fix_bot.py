#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py
=======================
Replaces {{ill|…}} templates on Shinto Wiki pages with
direct enwiki sitelinks (via Wikidata), handling numeric
and named parameters correctly and skipping any enwiki redirects.

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
def get_wikidata_qid(ja_title: str) -> str | None:
    """Lookup Japanese-title → Wikidata QID."""
    resp = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "sites":  "jawiki",
        "titles": ja_title,
    }, timeout=10)
    data = resp.json().get("entities", {})
    for ent in data.values():
        qid = ent.get("id")
        if qid and qid.startswith("Q"):
            return qid
    return None

def get_enwiki_title(qid: str) -> str | None:
    """Lookup QID → English Wikipedia title."""
    resp = requests.get("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "format": "json",
        "ids":    qid,
        "props":  "sitelinks",
        "sitefilter": "enwiki",
    }, timeout=10)
    ent = resp.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl.get("title") if sl else None

def enwiki_is_redirect(title: str) -> bool:
    """Check if an enwiki title is a redirect."""
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
def parse_ill_params(inner: str) -> tuple[dict[int,str], dict[str,str], list[str]]:
    """
    From the content of {{ill|…}} (inner), return:
      - num: dict of numeric index → value
      - named: dict of named param → value (e.g. lt, qq, etc.)
      - order: list of raw parts in original order
    Numeric overrides: any "3=foo" wins over bare positional at #3.
    """
    parts = [p.strip() for p in inner.split("|")]
    num   = {}
    named = {}
    # first, collect named and numeric assignments
    for p in parts:
        if "=" in p:
            key, val = p.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key.isdigit():
                num[int(key)] = val
            else:
                named[key] = val
    # then assign bare positional into next available numeric slots
    next_idx = 1
    for p in parts:
        if "=" in p:
            continue
        # bare positional
        while next_idx in num:
            next_idx += 1
        num[next_idx] = p
        next_idx += 1
    return num, named, parts

def choose_label(num: dict[int,str], named: dict[str,str]) -> str:
    """
    Decide the link label:
      1. named['lt'] if present
      2. else numeric[1], if present
      3. else fallback to empty string
    """
    if "lt" in named and named["lt"].strip():
        return named["lt"].strip()
    return num.get(1, "").strip()

def find_jawiki_title(num: dict[int,str], named: dict[str,str], parts: list[str]) -> str | None:
    """
    Find the Japanese title:
      - if named['ja'] exists, use that
      - else find each bare "ja" in parts, take its next bare or named value
      - return the last one found
    """
    if "ja" in named and named["ja"].strip():
        return named["ja"].strip()

    jawikis = []
    for i,p in enumerate(parts):
        if p == "ja":
            # next part if exists and not a numeric slot, take its raw text
            if i+1 < len(parts):
                jawikis.append(parts[i+1].strip())
        elif p.startswith("ja="):
            jawikis.append(p.split("=",1)[1].strip())

    return jawikis[-1] if jawikis else None

# ─── TEMPLATE REPLACEMENT ──────────────────────────────────────────
def repl(match):
    raw   = match.group(0)
    inner = match.group(1)
    num, named, parts = parse_ill_params(inner)

    print(f"  ▶ Found {{ill|…}}: {raw}")

    ja_title = find_jawiki_title(num, named, parts)
    if not ja_title:
        print("    ! No ja= found; skipping")
        return raw
    print(f"    → ja: {ja_title}")

    qid = get_wikidata_qid(ja_title)
    if not qid:
        print("    ! No Wikidata QID; skipping")
        return raw
    print(f"    → QID: {qid}")

    en_title = get_enwiki_title(qid)
    if not en_title:
        print("    ! No enwiki sitelink; skipping")
        return raw
    if enwiki_is_redirect(en_title):
        print(f"    ! enwiki:{en_title} is a redirect; skipping")
        return raw
    print(f"    → en: {en_title}")

    label = choose_label(num, named)
    if not label:
        print("    ! No label (lt or numeric[1]); skipping")
        return raw

    replacement = f"[[:en:{en_title}|{label}]]"
    print(f"    ✓ Replacing with {replacement}")
    return replacement

# ─── MAIN LOOP ────────────────────────────────────────────────────
def load_pages():
    if not os.path.exists(PAGES_FILE):
        open(PAGES_FILE, "w", encoding="utf-8").close()
        print(f"Created empty {PAGES_FILE}. Fill it and re-run.")
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
                          summary="Bot: replace {{ill}} with enwiki links via Wikidata")
                print("  → Page saved.\n")
            except APIError as e:
                print(f"  ! Save failed: {e}\n")
        else:
            print("  (no changes)\n")

        time.sleep(THROTTLE)

    print("All done.")

if __name__ == "__main__":
    main()
