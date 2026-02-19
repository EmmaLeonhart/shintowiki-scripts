#!/usr/bin/env python3
"""
cat_enwiki_overwrite.py
──────────────────────────────────────────────────────────────────
Overwrite every **sub‑category** in ``[[Category:Floating_Z_headings]]`` on
Shinto Miraheze with the identically titled category text from English
Wikipedia, then append

    [[Category:enwiki overwritten pages]]

Run with `-t/--test` for a dry‑run.
"""

# ── BASIC CONFIG ─────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"           # or set env MW_USER
PASSWORD   = "[REDACTED_SECRET_1]"         # or set env MW_PASS
THROTTLE   = 0.5                    # seconds between live saves

SRC_CAT    = "Floating_Z_headings"   # canon form w/ underscores
TRACK_CAT  = "enwiki overwritten pages"

# ── IMPORTS ─────────────────────────────────────────────────────-
import argparse, os, sys, time, mwclient
from mwclient.errors import APIError

# ── ARGPARSE / DRY‑RUN ───────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test", action="store_true", help="dry‑run")
args = parser.parse_args()

USERNAME = os.getenv("MW_USER", USERNAME)
PASSWORD = os.getenv("MW_PASS", PASSWORD)

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
enwiki = mwclient.Site("en.wikipedia.org")

print(f"Logged in as {USERNAME}")
if args.test:
    print("DRY‑RUN – no pages will be saved.")

# ── FETCH SUBCATEGORIES ─────────────────────────────────────────
try:
    cat_page = site.categories[SRC_CAT]
except (KeyError, APIError):
    sys.exit(f"Category:{SRC_CAT} not found – aborting.")

subcats = [p for p in cat_page if p.namespace == 14]  # namespace 14 = Category
print(f"Found {len(subcats)} sub‑categories in [[Category:{SRC_CAT}]].")
if not subcats:
    sys.exit("Nothing to do.")

# ── MAIN LOOP ───────────────────────────────────────────────────
for pg in subcats:
    title = pg.name  # already has "Category:" prefix
    print(f"→ {title}", flush=True)

    en_page = enwiki.pages[title]
    if not en_page.exists:
        print("  • skip (no en‑wiki match)")
        continue

    try:
        en_text = en_page.text()
    except APIError as e:
        print("  ! cannot fetch en‑wiki text:", e)
        continue

    new_text = en_text.rstrip() + f"\n\n[[Category:{TRACK_CAT}]]\n"

    try:
        old_text = pg.text()
    except APIError as e:
        print("  ! cannot fetch local text:", e)
        continue

    if new_text == old_text:
        print("  • unchanged")
        continue

    if args.test:
        print("  • would overwrite (dry‑run)")
        continue

    try:
        pg.save(new_text, summary="Bot: overwrite with content from en‑wiki")
        print("  ✓ saved")
    except APIError as e:
        print("  ! save failed:", e.code)

    time.sleep(THROTTLE)

print("Done.")
