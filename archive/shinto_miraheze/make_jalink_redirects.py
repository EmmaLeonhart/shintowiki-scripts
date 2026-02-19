#!/usr/bin/env python3
"""
make_jalink_redirects.py
──────────────────────────────────────────────────────────────────
For every title in **pages.txt**:
  • fetch that page
  • extract the first [[ja:Some Title]] inter-wiki link
  • create / update a new page  Jalink:Some Title
    whose text is               #redirect[[Original Page]]

Run with -t / --test for a dry-run (no saves).

Example
───────
    python make_jalink_redirects.py -t   # preview
    python make_jalink_redirects.py      # live run
"""

# ── BASIC CONFIG ────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 0.5                     # seconds between live saves

SUMMARY   = "Bot: create Jalink redirect from JA title"
PAGES_FILE = "pages.txt"

# ── IMPORTS ─────────────────────────────────────────────────────
import argparse, pathlib, re, sys, time, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ── REGEX ───────────────────────────────────────────────────────
JA_IW_RX = re.compile(r"\[\[\s*ja:([^\]]+?)]]", re.I)

# ── ARGPARSE ────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--test", action="store_true",
                help="dry-run (report only, no saves)")
args = ap.parse_args()

# ── LOAD TITLES ─────────────────────────────────────────────────
fp = pathlib.Path(PAGES_FILE)
if not fp.exists():
    sys.exit(f"{PAGES_FILE} not found – aborting.")

titles = [ln.strip().replace("_", " ")
          for ln in fp.read_text(encoding="utf8").splitlines()
          if ln.strip() and not ln.lstrip().startswith("#")]

if not titles:
    sys.exit(f"No titles in {PAGES_FILE} – aborting.")

print(f"Loaded {len(titles)} title(s) from {PAGES_FILE}.")

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}.")
if args.test:
    print("DRY-RUN mode – no pages will be saved.")

# ── MAIN LOOP ───────────────────────────────────────────────────
for orig_title in titles:
    orig_page = site.pages[orig_title]
    print("→", orig_page.name, end=" … ", flush=True)

    if not orig_page.exists:
        print("skip (does not exist)")
        continue

    try:
        txt = orig_page.text()
    except (APIError, InvalidPageTitle):
        print("skip (cannot fetch)")
        continue

    m = JA_IW_RX.search(txt)
    if not m:
        print("skip (no ja-iw)")
        continue

    ja_title = m.group(1).strip()
    if not ja_title:
        print("skip (empty ja-title)")
        continue

    jalink_title = f"Jalink:{ja_title}"
    redirect_text = f"#redirect[[{orig_page.name}]]\n"

    jalink_page = site.pages[jalink_title]
    action = "would create" if args.test else "created/updated"

    if args.test:
        if jalink_page.exists:
            print(f"would update → {jalink_title}")
        else:
            print(f"would create → {jalink_title}")
        continue

    try:
        jalink_page.save(redirect_text, summary=SUMMARY)
        print(f"{action}")
    except APIError as e:
        print(f"! failed ({e.code})")
    time.sleep(THROTTLE)

print("Done.")
