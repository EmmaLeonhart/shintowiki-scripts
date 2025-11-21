#!/usr/bin/env python3
"""
cat_empty_section_trim.py
─────────────────────────
Delete *empty* sections from every page in the Category namespace.

An “empty section” is:

    ==Some heading==
    (only blank lines and/or <!-- comments -->)
    ==Next heading==   ← or EOF

Usage
─────
    python cat_empty_section_trim.py          # full sweep
    python cat_empty_section_trim.py Heian    # resume at ≥ Category:Heian…
"""

# ── BASIC CONFIG ────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 0.4                       # seconds between edits

# ── IMPORTS ─────────────────────────────────────────────────────
import re, sys, time, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ── SESSIONS ────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# ── REGEX ───────────────────────────────────────────────────────
EMPTY_SEC_RX = re.compile(
    r"(?ms)^[ \t]*==[^=\n]+?==[ \t]*\n"          # the heading line
    r"(?:[ \t]*<!--.*?-->[ \t]*\n|[ \t]*\n)*"    # only comments / blanks
    r"(?=^[ \t]*==|\Z)"                          # look-ahead to next head / EOF
)

# ── OPTIONAL START POINT ───────────────────────────────────────
start_at = None
if len(sys.argv) > 1:
    start_at = sys.argv[1].strip("'\"")
    if not start_at.lower().startswith("category:"):
        start_at = f"Category:{start_at}"

print("Logged in – trimming empty sections in NS-14")
if start_at:
    print(f"(starting at ≥ {start_at})")

# ── WALK THE CATEGORY NAMESPACE ────────────────────────────────
apc       = None
passed    = not bool(start_at)

while True:
    q = {"action":"query","list":"allpages","apnamespace":14,
         "aplimit":"max","format":"json"}
    if apc:
        q["apcontinue"] = apc

    batch = site.api(**q)

    for a in batch["query"]["allpages"]:
        title = a["title"]
        if not passed and title < start_at:
            continue
        passed = True

        pg = site.pages[title]
        try:
            orig = pg.text()
        except (InvalidPageTitle, APIError):
            print("→", title, " – fetch failed")
            continue

        new = EMPTY_SEC_RX.sub("", orig).rstrip() + "\n"

        if new != orig:
            try:
                pg.save(new, summary="Bot: remove empty section(s)")
                print("→", title, " • cleaned")
            except APIError as e:
                print("→", title, " – save failed:", e.code)
            time.sleep(THROTTLE)
        else:
            print("→", title, " • ok")

    apc = batch.get("continue", {}).get("apcontinue")
    if not apc:
        break

print("Finished.")
