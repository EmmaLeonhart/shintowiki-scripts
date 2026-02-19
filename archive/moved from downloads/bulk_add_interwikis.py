#!/usr/bin/env python3
"""
bulk_add_interwikis.py – add / fix many rows on Special:Interwiki
-----------------------------------------------------------------
usage:  python bulk_add_interwikis.py  [file.csv]

The CSV must contain:  prefix,baseURL   (without $1).
"""

import csv, sys, time, urllib.parse, mwclient
from mwclient.errors import APIError

# ── YOUR WIKI & BOT ACCOUNT ────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"      #  ❰ change ❱
LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle"               #  ❰ change ❱
PASSWORD   = "[REDACTED_SECRET_2]"             #  ❰ change ❱
THROTTLE   = 0.4                        # seconds between API writes
CSV_FILE   = sys.argv[1] if len(sys.argv) > 1 else "interwikis.csv"

FORWARD = "1"        # 1 = yes , 0 = no
TRANS   = "1"        # 1 = yes , 0 = no

# ───────────────────────────────────────────────────────────────

site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in on {LOCAL_URL} as {USERNAME}")

def add_or_update(prefix:str, url:str):
    """Create or fix an interwiki‐row via ManageWiki."""
    # ManageWiki requires the URL to contain $1
    if "$1" not in url:
        if not url.endswith("/"):
            url += "/"
        url += "$1"

    payload = {
        "action": "managewiki",
        "format": "json",
        "mod": "interwiki",

        "wpInterwikiPrefix":   prefix,
        "wpInterwikiURL":      url,
        "wpInterwikiForward":  FORWARD,   # 1/0
        "wpInterwikiTrans":    TRANS,     # 1/0

        # tell the module we’re *adding* (creates or updates)
        "wpInterwikiAdd": "1",
        "token": site.get_token("csrf")
    }

    try:
        result = site.api(**payload)
        if result.get("managewiki", {}).get("success"):
            print(f" • {prefix:5} → added/updated")
        else:
            print(f" ! {prefix:5} → API said: {result}")
    except APIError as e:
        print(f" ! {prefix:5} → API error: {e.code}")
    time.sleep(THROTTLE)

# ── read the CSV and process lines ─────────────────────────────
with open(CSV_FILE, encoding="utf-8") as fh:
    reader = csv.reader(fh)
    for row in reader:
        if not row or row[0].strip().startswith("#"):
            continue
        if len(row) < 2:
            print(" ! skipped malformed line:", row)
            continue
        add_or_update(row[0].strip(), row[1].strip())

print("Done.")
