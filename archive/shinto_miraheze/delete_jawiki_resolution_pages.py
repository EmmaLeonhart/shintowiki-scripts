#!/usr/bin/env python3
"""
delete_jawiki_resolution_pages.py
──────────────────────────────────────────────────────────────────
Deletes all pages in Category:Jawiki_resolution_pages.

Pass -t / --test for a dry-run (reports what *would* be deleted).

Example
───────
    python delete_jawiki_resolution_pages.py -t      # preview
    python delete_jawiki_resolution_pages.py         # actually delete
"""

# ── BASIC CONFIG ────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 0.5                     # seconds between live deletions

CATEGORY_NAME = "Jawiki resolution pages"
DELETE_REASON = "Bot: mass deletion of Jawiki resolution pages"

# ── IMPORTS ─────────────────────────────────────────────────────
import argparse, sys, time, io
import mwclient
from mwclient.errors import APIError

# Fix Windows Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── ARGPARSE ────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--test", action="store_true",
                help="dry-run (report only, no deletions)")
args = ap.parse_args()

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}.")
if args.test:
    print("DRY-RUN mode – no pages will be deleted.")

# ── GET PAGES FROM CATEGORY ─────────────────────────────────────
cat = site.categories[CATEGORY_NAME]
print(f"Fetching pages from Category:{CATEGORY_NAME}...")

deleted_count = 0
skipped_count = 0
failed_count = 0

# ── MAIN LOOP ───────────────────────────────────────────────────
for pg in cat:
    print(f"→ {pg.name}", end=" … ", flush=True)

    if not pg.exists:
        print("skip (does not exist)")
        skipped_count += 1
        continue

    if args.test:
        print("would delete (dry-run)")
        deleted_count += 1
        continue

    try:
        pg.delete(reason=DELETE_REASON)
        print("✓ deleted")
        deleted_count += 1
    except APIError as e:
        print(f"! failed ({e.code})")
        failed_count += 1
    time.sleep(THROTTLE)

print()
print(f"Done. Deleted: {deleted_count}, Skipped: {skipped_count}, Failed: {failed_count}")
