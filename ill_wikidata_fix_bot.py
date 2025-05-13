#!/usr/bin/env python3
import os, sys, re, time
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
    """Look up a Japanese‐wiki title on Wikidata to get its Q-ID."""
    params = {
        "action":  "wbgetentities",
        "format":  "json",
        "sites":   "jawiki",
        "titles":  ja_title,
    }
    r = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=10)
    data = r.json().get("entities", {})
    for ent in data.values():
        qid = ent.get("id")
        if qid and not qid.startswith("-"):
            return qid
    return None

def get_enwiki_title(qid: str) -> str | None:
    """Given a Q-ID, return the enwiki sitelink title or None."""
    params = {
        "action":     "wbgetentities",
        "format":     "json",
        "ids":        qid,
        "props":      "sitelinks",
        "sitefilter": "enwiki",
    }
    r = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=10)
    ent = r.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {}).get("enwiki")
    return sl.get("title") if sl else None

def enwiki_is_redirect(title: str) -> bool:
    """Check on en.wikipedia.org whether this page is a redirect."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop":   "info",
    }
    r = requests.get("https://en.wikipedia.org/w/api.php", params=params, timeout=10)
    pages = r.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    return "redirect" in page

# ─── PARAMETER PARSING ─────────────────────────────────────────────
def choose_label(parts: list[str]) -> str:
    # last lt=
    lts = [p.split("=",1)[1] for p in parts if p.startswith("lt=")]
    if lts:
        return lts[-1]
    # last 1=
    ones = [p.split("=",1)[1] for p in parts if p.startswith("1=")]
    if ones:
        return ones[-1]
    # fallback: the very first param
    return parts[0]

# ─── TEMPLATE REPLACEMENT ──────────────────────────────────────────
def repl(match):
    raw = match.group(0)
    inner = match.group(1)
    parts = [p.strip() for p in inner.split("|")]
    print(f"  ▶ found {{ill|…}} → {raw}")

    # find all ja-indices
    idxs = [i for i,p in enumerate(parts)
            if p.split("=",1)[-1] == "ja"]
    if not idxs or idxs[-1] + 1 >= len(parts):
        print("    ! no ja:… param found, skipping")
        return raw

    ja_part = parts[idxs[-1] + 1]
    ja_title = ja_part.split("=",1)[-1]
    print(f"    → ja: {ja_title}")

    qid = get_wikidata_qid(ja_title)
    if not qid:
        print(f"    ! no Q-ID for '{ja_title}', skipping")
        return raw

    en_title = get_enwiki_title(qid)
    if not en_title:
        print(f"    ! no enwiki sitelink for Q-ID {qid}, skipping")
        return raw

    if enwiki_is_redirect(en_title):
        print(f"    ! enwiki:[[en:{en_title}]] is a redirect, skipping")
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
