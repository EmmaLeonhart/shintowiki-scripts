#!/usr/bin/env python3
"""
cat_wikidata_prepender.py
──────────────────────────────────────────────────────────────────
Read page titles from **pages.txt** (one per line). For each listed page in
NS‑0 on shinto.miraheze.org:

1. If an AFC comment is already present, skip.
2. Search the wikitext for a ja‑wiki inter‑wiki link ( ``[[ja:Foo]]`` ).
3. Follow that link to grab the page‑property ``wikibase_item`` (Q‑id).
4. Prepend a comment block:

       {{afc comment|Wikidata entry [[d:Q1234]]
       Wikidata name: NAME
       ~~~~}}

5. If the Q‑id has **no English label**, append
   ``[[Category:pages without english wikidata name]]``.
6. If *no* Q‑id exists, append
   ``[[Category:paes with no wikidata]]`` (typo preserved).

Run with ``-t`` / ``--test`` to preview changes without saving.
"""

# ── BASIC CONFIG ─────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"           # or set env MW_USER
PASSWORD   = "[REDACTED_SECRET_1]"         # or set env MW_PASS
THROTTLE   = 0.5                    # seconds between live saves
PAGES_FILE = "pages.txt"            # titles list

# ── IMPORTS ─────────────────────────────────────────────────────-
import argparse, os, sys, time, re, requests, pathlib, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ── REGEX PATTERNS ──────────────────────────────────────────────
JA_IW_RX = re.compile(r"\[\[\s*ja:([^]\n]+?)]]", re.I)
AFCC_RX  = re.compile(r"\{\{\s*afc comment\|", re.I)

# ── ARGPARSE / DRY‑RUN ───────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test", action="store_true", help="dry‑run (no saves)")
args = parser.parse_args()

USERNAME = os.getenv("MW_USER", USERNAME)
PASSWORD = os.getenv("MW_PASS", PASSWORD)

# ── LOGIN ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")
if args.test:
    print("DRY‑RUN – no pages will be saved.")

jawiki = mwclient.Site("ja.wikipedia.org")
WD_API = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
NO_EN_CAT = "[[Category:pages without english wikidata name]]"
NO_WD_CAT = "[[Category:paes with no wikidata]]"   # typo intentional

# ── LOAD PAGES.TXT ──────────────────────────────────────────────
plist = pathlib.Path(PAGES_FILE)
if not plist.exists():
    sys.exit(f"{PAGES_FILE} not found – aborting.")

titles = [ln.strip().replace("_", " ") for ln in plist.read_text(encoding="utf8").splitlines()
          if ln.strip() and not ln.startswith("#")]
print(f"Loaded {len(titles)} titles from {PAGES_FILE}.")
if not titles:
    sys.exit("No titles to process – aborting.")

# ── HELPER FUNCTIONS ────────────────────────────────────────────

def get_wikidata_id(ja_title: str) -> str | None:
    try:
        res = jawiki.api(action="query", prop="pageprops", titles=ja_title, format="json")
        page = next(iter(res["query"]["pages"].values()))
        return page.get("pageprops", {}).get("wikibase_item")
    except Exception:
        return None


def get_en_label(qid: str) -> str | None:
    try:
        data = requests.get(WD_API.format(qid), timeout=10).json()
        ent = data["entities"][qid]
        return ent["labels"].get("en", {}).get("value")
    except Exception:
        return None

# ── MAIN LOOP ───────────────────────────────────────────────────
for title in titles:
    pg = site.pages[title]
    print(f"→ {title}", flush=True)

    try:
        text = pg.text()
    except (APIError, InvalidPageTitle):
        print("  ! cannot fetch page text")
        continue



    m = JA_IW_RX.search(text)
    if not m:
        print("  • skip (no ja‑wiki link)")
        continue

    ja_title = m.group(1).strip()
    qid = get_wikidata_id(ja_title)

    if qid:
        label = get_en_label(qid)
        comment = (f"{{{{afc comment|Wikidata entry [[d:{qid}]]\n"
                   f"Wikidata name: {label or '(none)'}\n~~~~}}}}\n")
        tail_cat = "" if label else f"\n{NO_EN_CAT}"
    else:
        comment = ("{{afc comment|Wikidata entry (none)\n"
                   "Wikidata name: (none)\n~~~~}}\n")
        tail_cat = f"\n{NO_WD_CAT}"

    new_text = comment + text + tail_cat

    if args.test:
        print("  • would save (dry‑run)")
        continue

    try:
        pg.save(new_text, summary="Bot: prepend Wikidata AFC comment via pages.txt")
        print("  ✓ saved")
    except APIError as e:
        print("  ! save failed:", e.code)

    time.sleep(THROTTLE)

print("Done.")
