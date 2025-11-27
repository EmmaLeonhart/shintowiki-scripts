#!/usr/bin/env python3
"""
delete_pages.py
──────────────────────────────────────────────────────────────────
Deletes every page whose title is listed in **pages.txt**.

* One title per line (comment lines starting with # are ignored).
* Titles may be written with underscores or spaces; either is fine.
* Pass -t / --test for a dry-run (reports what *would* be deleted).

Example
───────
    python delete_pages.py -t      # preview
    python delete_pages.py         # actually delete
"""

# ── BASIC CONFIG ────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 0.5                     # seconds between live deletions

DELETE_REASON = "Bot: mass deletion requested via pages.txt"

PAGES_FILE = "pages.txt"

# ── IMPORTS ─────────────────────────────────────────────────────
import argparse, pathlib, sys, time, mwclient
from mwclient.errors import APIError

# ── ARGPARSE ────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--test", action="store_true",
                help="dry-run (report only, no deletions)")
args = ap.parse_args()

# ── LOAD TITLES FROM pages.txt ─────────────────────────────────
f = pathlib.Path(PAGES_FILE)
if not f.exists():
    sys.exit(f"{PAGES_FILE} not found – aborting.")

titles = [ln.strip().replace("_", " ")
          for ln in f.read_text(encoding="utf8").splitlines()
          if ln.strip() and not ln.lstrip().startswith("#")]

if not titles:
    sys.exit(f"No titles found in {PAGES_FILE} – aborting.")

print(f"Loaded {len(titles)} title(s) from {PAGES_FILE}.")

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}.")
if args.test:
    print("DRY-RUN mode – no pages will be deleted.")

# ── MAIN LOOP ───────────────────────────────────────────────────
for t in titles:
    pg = site.pages[t]
    print("→", pg.name, end=" … ", flush=True)

    if not pg.exists:
        print("skip (does not exist)")
        continue

    if args.test:
        print("would delete (dry-run)")
        continue

    try:
        pg.delete(reason=DELETE_REASON)
        print("✓ deleted")
    except APIError as e:
        # e.code is something like "permissiondenied" or "missingtitle"
        print(f"! failed ({e.code})")
    time.sleep(THROTTLE)

print("Done.")
