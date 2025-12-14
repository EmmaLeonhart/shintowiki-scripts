# ==========================================================================
#  cat_enwiki_overwrite.py  (already tested)
# ===========================================================================
# [ existing code retained here … ]
# ────────────────────────────────────────────────────────────────────────────
# (The full code of cat_enwiki_overwrite.py is unchanged and remains above.)


# ===========================================================================
#  cat_clean_float_z.py  —  NEW helper script
# ===========================================================================
#!/usr/bin/env python3
"""
cat_clean_float_z.py
──────────────────────────────────────────────────────────────────
For every *sub‑category* inside ``[[Category:Floating_Z_headings]]`` on the
Shinto Miraheze wiki, scrub the page so that **only**:

  • inter‑wiki links ( ``[[xx:Title]]`` )
  • category declarations ( ``[[Category:…]]`` )

remain in the wikitext. All other lines—templates, stray prose, headings,
etc.—are discarded.

A convenient `-t/--test` flag shows the diff without saving.
"""

# ── BASIC CONFIG ─────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"           # or set env MW_USER
PASSWORD   = "[REDACTED_SECRET_1]"         # or set env MW_PASS
THROTTLE   = 0.5                    # seconds between live saves

SRC_CAT    = "Floating_Z_headings"   # parent category to scan

# ── IMPORTS ─────────────────────────────────────────────────────-
import argparse, os, sys, time, re, mwclient
from mwclient.errors import APIError

# ── PATTERNS ─────────────────────────────────────────────────────
CAT_LINE = re.compile(r"^\s*\[\[\s*Category:[^]]+]]\s*$", re.I)
IW_LINE  = re.compile(r"^\s*\[\[\s*[a-z\-]+:[^]]+]]\s*$", re.I)

# ── ARGPARSE / DRY‑RUN ───────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test", action="store_true", help="dry‑run")
args = parser.parse_args()

USERNAME = os.getenv("MW_USER", USERNAME)
PASSWORD = os.getenv("MW_PASS", PASSWORD)

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")
if args.test:
    print("DRY‑RUN – no pages will be saved.")

# ── GATHER SUB‑CATEGORIES ───────────────────────────────────────
try:
    parent_cat = site.categories[SRC_CAT]
except (KeyError, APIError):
    sys.exit(f"Category:{SRC_CAT} not found – aborting.")

subs = [p for p in parent_cat if p.namespace == 14]
print(f"Found {len(subs)} sub‑categories in [[Category:{SRC_CAT}]].")
if not subs:
    sys.exit("Nothing to clean.")

# ── MAIN LOOP ───────────────────────────────────────────────────
for pg in subs:
    title = pg.name
    print(f"→ {title}", flush=True)

    try:
        old_text = pg.text()
    except APIError as e:
        print("  ! cannot fetch text:", e)
        continue

    # keep only inter‑wikis and category lines
    kept = [ln.strip() for ln in old_text.splitlines()
            if IW_LINE.match(ln) or CAT_LINE.match(ln)]

    new_text = "\n".join(dict.fromkeys(kept)) + "\n"  # dedupe & tidy

    if new_text == old_text:
        print("  • unchanged (already clean)")
        continue

    if args.test:
        print("  • would overwrite with cleaned version (dry‑run)")
        continue

    try:
        pg.save(new_text, summary="Bot: remove non‑IW/non‑Category content")
        print("  ✓ saved")
    except APIError as e:
        print("  ! save failed:", e.code)

    time.sleep(THROTTLE)

print("Done.")
