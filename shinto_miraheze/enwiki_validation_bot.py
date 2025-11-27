#!/usr/bin/env python3
"""
enwiki_validation_bot.py – verify and clean up enwiki interwiki links
---------------------------------------------------------------------
For every page listed in **pages.txt** this bot:

1. Collects **all** `[[en:…]]` inter‑wiki links in the page wikitext.
2. Tests each link against *en.wikipedia.org* (redirects count as existing).
3. Removes every *invalid* enwiki link from the wikitext (saves only if
   something changed).
4. Classifies the page with one of three tracking categories, appending it
   only if not already present:

   * `[[Category:translated pages with valid en interwikis]]`  – page has at
     least one valid en‑link **and** a `{{translated page|…}}` template.
   * `[[Category:pages with valid en interwikis]]`              – page has at
     least one valid en‑link but **no** translated‑page template.
   * `[[Category:pages without valid translation templates or en interwikis]]`
     – page ends up with **no** en‑links and **no** translated‑page template.

Nothing is ever deleted; the bot only edits links and categories.
"""

import os, sys, re, time, urllib.parse, requests, mwclient
from typing import List, Tuple

# ─── CONFIG ───────────────────────────────────────────────────────────
SHINTO_URL  = "shinto.miraheze.org"
SHINTO_PATH = "/w/"

USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"           # use env‑var / keyring in production

PAGES_FILE = "pages.txt"
THROTTLE    = 0.1             # seconds between writes

# ─── MW SESSIONS ──────────────────────────────────────────────────────
print(f"Connecting to {SHINTO_URL} …")
site_local = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site_local.login(USERNAME, PASSWORD)
print("  ↳ logged in ✔")

en_site = mwclient.Site("en.wikipedia.org", path="/w/")  # read‑only

# ─── REGEXES ──────────────────────────────────────────────────────────
EN_IW_RE = re.compile(r"\[\[\s*en\s*:\s*([^\]|]+)", re.I)
TRANS_TMPL_RE = re.compile(r"\{\{\s*translated\s*page\s*\|", re.I)

# ─── HELPERS ──────────────────────────────────────────────────────────

def load_titles(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def find_en_links(text: str) -> List[str]:
    """Return *raw* titles from every en‑link in text."""
    return [urllib.parse.unquote(m.group(1)).replace("_", " ")
            for m in EN_IW_RE.finditer(text)]


def en_page_exists(title: str) -> bool:
    page = en_site.pages[title]
    try:
        return page.exists
    except Exception:
        return False


def strip_invalid_links(text: str, invalid_titles: List[str]) -> Tuple[str, bool]:
    """Remove every [[en:…]] line whose *target* is in *invalid_titles*.
    Returns (new_text, changed?)."""
    if not invalid_titles:
        return text, False

    # build one combined regex for speed
    escaped = [re.escape(t) for t in invalid_titles]
    patt = re.compile(r"^.*\[\[\s*en\s*:\s*(?:" + "|".join(escaped) + r")\s*(?:\|[^\]]*)?\]\].*$",
                      re.I | re.M)
    new_text, n = patt.subn("", text)
    if n:
        # Collapse possible double blanks from removed lines
        new_text = re.sub(r"\n{3,}", "\n\n", new_text.strip()) + "\n"
    return new_text, bool(n)


def append_category_if_missing(page, cat_line: str, summary: str):
    try:
        txt = page.text()
    except Exception as e:
        print(f"    ! read failed: {e}")
        return
    if cat_line in txt:
        return
    new_txt = txt.rstrip() + "\n" + cat_line + "\n"
    try:
        page.save(new_txt, summary=summary)
        print("      · category appended")
    except mwclient.errors.APIError as e:
        print(f"    ! save failed: {e.code}")


# ─── MAIN PROCESSOR ───────────────────────────────────────────────────

def process_page(title: str):
    pg = site_local.pages[title]
    if not pg.exists:
        print("  ! page missing – skipped")
        return

    text = pg.text()
    raw_links = find_en_links(text)
    has_translated = bool(TRANS_TMPL_RE.search(text))

    if not raw_links:
        if not has_translated:
            append_category_if_missing(
                pg,
                "[[Category:pages without valid translation templates or en interwikis]]",
                "Bot: classify – no translation template or en interwikis",
            )
        else:
            print("    · translated template but no enwiki link – left untouched")
        return

    # Determine validity of each link
    valid_titles, invalid_titles = [], []
    for t in raw_links:
        (valid_titles if en_page_exists(t) else invalid_titles).append(t)

    # Remove invalid links, if any
    if invalid_titles:
        new_text, changed = strip_invalid_links(text, invalid_titles)
        if changed:
            try:
                pg.save(new_text, summary="Bot: remove invalid enwiki interwiki links")
                print(f"    · removed {len(invalid_titles)} invalid link(s)")
                text = new_text  # use updated version for further checks
            except mwclient.errors.APIError as e:
                print(f"    ! save failed while stripping links: {e.code}")

    # After cleanup, re‑evaluate remaining en‑links
    remaining_links = find_en_links(text)
    if remaining_links:
        cat = (
            "[[Category:translated pages with valid en interwikis]]"
            if has_translated else
            "[[Category:pages with valid en interwikis]]"
        )
        append_category_if_missing(pg, cat, "Bot: classify by valid enwiki interwikis")
    elif not has_translated:
        append_category_if_missing(
            pg,
            "[[Category:pages without valid translation templates or en interwikis]]",
            "Bot: classify – no translation template or en interwikis",
        )


# ─── MAIN LOOP ───────────────────────────────────────────────────────

def main():
    titles = load_titles(PAGES_FILE)
    for idx, t in enumerate(titles, 1):
        print(f"\n{idx}/{len(titles)} → [[{t}]]")
        process_page(t)
        time.sleep(THROTTLE)

    print("\nDone.")


if __name__ == "__main__":
    main()
