#!/usr/bin/env python3
"""
cat_jawiki_cleanup.py
──────────────────────────────────────────────────────────────────
For every Category page that…

  • contains a ja-interwiki      ([[ja:…]])
  • contains NO en-interwiki     ([[en:…]])

…rewrite the page so that only *templates*, *inter­wikis* and
*[[Category:…]]* lines remain, arranged like this:

    ==Japanese Content==
    <full ja-wiki wikitext except its category lines>
    [[Category:Categories needing translation of Japanese explanatory text]]

    ==Local Content==
    <templates, interwikis and category lines from the local page>

Everything else (random headings, stray prose, broken inter-wiki
fragments, etc.) is discarded.

How it chooses pages
────────────────────
* If **pages.txt** is present in the working directory, only the titles
  listed there (one per line, with or without “Category:” prefix) are
  processed.
* Otherwise the script walks the *entire* Category namespace.

Call examples
─────────────
    python cat_jawiki_cleanup.py          # whole NS-14
    python cat_jawiki_cleanup.py -t 1     # dry-run (no saves)

Use “-t” / “--test” to run in **dry mode** – you’ll see what *would* be
edited without actually saving.

You may also give a start-title (just like earlier bots):

    python cat_jawiki_cleanup.py "Foo"    # begin at/after Category:Foo
"""

# ── BASIC CONFIG ─────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5                  # seconds between live saves

# tracking cat to append
TRACK_CAT  = "Categories needing translation of Japanese explanatory text"

# ── IMPORTS ──────────────────────────────────────────────────────
import argparse, re, sys, time, pathlib, mwclient, requests
from mwclient.errors import APIError, InvalidPageTitle

# ── REGEXES ──────────────────────────────────────────────────────
JA_IW_RX   = re.compile(r"\[\[\s*ja:([^\]]+?)]]", re.I)
EN_IW_RX   = re.compile(r"\[\[\s*en:[^\]]+]]", re.I)
CAT_LINE   = re.compile(r"^\s*\[\[\s*Category:[^\]]+]]\s*$", re.I)
IW_LINE    = re.compile(r"^\s*\[\[\s*[a-z\-]+:[^\]]+]]\s*$", re.I)
TPL_LINE   = re.compile(r"^\s*\{\{[^{}]+}}\s*$")      # one-liner templates

# ── ARGPARSE / DRY-RUN OPTION ────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("start", nargs="?", help="start at/after this Category")
ap.add_argument("-t","--test", action="store_true", help="dry-run (no saves)")
args = ap.parse_args()

start_at = None
if args.start:
    start_at = args.start.strip("'\"")
    if not start_at.lower().startswith("category:"):
        start_at = f"Category:{start_at}"

# ── SESSIONS ─────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
jawiki = mwclient.Site("ja.wikipedia.org")

print("Logged in.")
if args.test:
    print("DRY-RUN mode – no pages will be saved.")
if start_at:
    print(f"Start at ≥ {start_at}")

# ── UTIL: fetch JA wikitext (w/out its categories) ───────────────
def fetch_ja_content(ja_title:str) -> str|None:
    if "[" in ja_title or "]" in ja_title:
        return None
    try:
        jp = jawiki.pages[
            ja_title if ja_title.startswith("Category:")
            else f"Category:{ja_title}"
        ]
    except (InvalidPageTitle, KeyError):
        return None
    if not jp.exists:
        return None

    txt = jp.text()
    # drop JA categories
    body = "\n".join(l for l in txt.splitlines() if not CAT_LINE.match(l)).strip()
    return body or None

# ── PAGE SOURCE LIST ─────────────────────────────────────────────
def load_pages_txt() -> list[str]|None:
    f = pathlib.Path("pages.txt")
    if not f.exists():
        return None
    titles = []
    for ln in f.read_text(encoding="utf8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if not ln.lower().startswith("category:"):
            ln = f"Category:{ln}"
        titles.append(ln)
    return titles or None

pages_from_file = load_pages_txt()

# ── MAIN LOOP ────────────────────────────────────────────────────
def tidy(pg):
    try:
        orig = pg.text()
    except (APIError, InvalidPageTitle):
        print("  ! cannot fetch")
        return

    # bail if no ja-link or already has en-link
    m = JA_IW_RX.search(orig)
    if not m or EN_IW_RX.search(orig):
        print("  • skip (no ja-iw or has en-iw)")
        return

    ja_title = m.group(1).strip()
    ja_text  = fetch_ja_content(ja_title)
    if not ja_text:
        print("  • skip (cannot fetch JA page)")
        return

    # ── split local page into kept lines ───────────────────────
    keep_lines = []
    for ln in orig.splitlines():
        if TPL_LINE.match(ln) or IW_LINE.match(ln) or CAT_LINE.match(ln):
            keep_lines.append(ln.strip())

    # tidy duplicates & make sure tracking cat present
    keep_lines = list(dict.fromkeys(keep_lines))   # preserve order, dedupe
    if f"[[Category:{TRACK_CAT}]]" not in keep_lines:
        keep_lines.append(f"[[Category:{TRACK_CAT}]]")

    # ── new wikitext ────────────────────────────────────────────
    new_txt = (
        "==Japanese Content==\n"
        f"{ja_text}\n"
        f"[[Category:{TRACK_CAT}]]\n\n"
        "==Local Content==\n" +
        "\n".join(keep_lines).rstrip() + "\n"
    )

    if new_txt == orig:
        print("  • unchanged")
        return

    if args.test:
        print("  • would update (dry-run)")
        return

    try:
        pg.save(new_txt, summary="Bot: replace with clean JA/Local structure")
        print("  ✓ saved")
    except APIError as e:
        print("  ! save failed:", e.code)
    time.sleep(THROTTLE)

# ── ITERATION LOGIC ──────────────────────────────────────────────
if pages_from_file:
    print("Processing pages from pages.txt …")
    for t in pages_from_file:
        print("→", t)
        tidy(site.pages[t])
else:
    print("Processing *all* Category pages …")
    apc = None
    passed = not bool(start_at)
    while True:
        q = {"action":"query","list":"allpages","apnamespace":14,
             "aplimit":"max","format":"json"}
        if apc: q["apcontinue"] = apc
        batch = site.api(**q)

        for e in batch["query"]["allpages"]:
            title = e["title"]
            if not passed:
                if title < start_at:
                    continue
                passed = True
            print("→", title)
            tidy(site.pages[title])

        apc = batch.get("continue", {}).get("apcontinue")
        if not apc:
            break

print("Done.")
