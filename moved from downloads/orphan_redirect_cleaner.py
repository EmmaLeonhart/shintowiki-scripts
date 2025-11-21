#!/usr/bin/env python3
"""
orphan_redirect_cleaner.py
==========================

Delete orphaned redirects in main-space.

• “Redirect”   = page whose wikitext starts with `#REDIRECT`.
• “Orphaned”   = no backlinks except other redirects
                 (i.e. `blfilterredir=nonredirects` returns nothing).

Usage
-----
    python orphan_redirect_cleaner.py            # full sweep
    python orphan_redirect_cleaner.py "Foo"      # resume at ≥ “Foo”
"""

# ─── BASIC CONFIG ────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"
LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 0.3                 # seconds between deletions
SUMMARY    = "Bot: delete orphaned redirect"

# ─── IMPORTS ─────────────────────────────────────────────────────
import re, sys, time, mwclient
from mwclient.errors import APIError, InvalidPageTitle

START_AT = sys.argv[1] if len(sys.argv) > 1 else None
if START_AT and not START_AT.lower().startswith("category:"):
    START_AT = START_AT            # plain page title in main-space

REDIR_RX = re.compile(r"^\s*#redirect", re.I)

# ─── SESSION ────────────────────────────────────────────────────
site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
site.login(USERNAME, PASSWORD)
print("Logged in – scanning main-space redirects …")
if START_AT:
    print(f"(will start at ≥ “{START_AT}”)")

# ─── WALK ALL MAIN-SPACE REDIRECTS ──────────────────────────────
apc           = None
passed_start  = not bool(START_AT)

while True:
    q = {
        "action":        "query",
        "list":          "allpages",
        "apnamespace":    0,
        "apfilterredir": "redirects",
        "aplimit":       "max",
        "format":        "json"
    }
    if apc:
        q["apcontinue"] = apc

    batch = site.api(**q)

    for entry in batch["query"]["allpages"]:
        title = entry["title"]

        # handle resume point
        if not passed_start:
            if title < START_AT:
                continue
            passed_start = True

        try:
            pg = site.pages[title]
        except (InvalidPageTitle, KeyError, APIError):
            print(f" ! API issue on {title} – skipped")
            continue

        # double-check that it is a redirect
        if not REDIR_RX.match(pg.text()):
            continue

        # look for at least ONE non-redirect backlink
        bl = site.api(
            action="query", list="backlinks",
            bltitle=title, blfilterredir="nonredirects",
            bllimit=1, format="json"
        )["query"]["backlinks"]

        if bl:
            print(f" • {title} – has backlinks (kept)")
            continue     # not orphaned

        # orphaned ⇒ delete
        try:
            pg.delete(reason=SUMMARY, watch=False)
            print(f" • {title} – orphaned redirect deleted ✓")
        except APIError as e:
            print(f" ! {title} – deletion failed ({e.code})")

        time.sleep(THROTTLE)

    apc = batch.get("continue", {}).get("apcontinue")
    if not apc:
        break

print("Finished orphan-redirect sweep.")
