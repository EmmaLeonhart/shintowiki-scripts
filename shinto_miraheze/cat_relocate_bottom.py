#!/usr/bin/env python3
"""
cat_relocate_bottom.py
──────────────────────
Sweep the Category namespace (NS-14) and:

  • move every [[Category:…]] link,
  • move every language inter-wiki  [[xx:…]],
  • move every {{translated page|…}} template,

to a *single* bottom section headed  ==Categories== .
All three groups are deduplicated and alphabetically sorted.

Usage
─────
    python cat_relocate_bottom.py          # full run
    python cat_relocate_bottom.py FooBar   # start at ≥ Category:FooBar…
"""

# ── BASIC CONFIG ────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 0.5                        # seconds between saves

# ── IMPORTS ─────────────────────────────────────────────────────
import re, sys, time, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ── SESSIONS ────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# ── REGEXES ─────────────────────────────────────────────────────
CAT_RX  = re.compile(r"\[\[\s*Category\s*:[^\]]+]]", re.I)
IW_RX   = re.compile(r"\[\[\s*[a-z\-]{2,12}:[^\]]+]]", re.I)   # xx:Title
TPL_RX  = re.compile(r"\{\{\s*translated\s+page[^{}]*\}\}", re.I | re.S)
HEAD_RX = re.compile(r"^==\s*Categories\s*==\s*$", re.I | re.M)

# ── HELPERS ─────────────────────────────────────────────────────
def pull_groups(text:str):
    """Return (cats, interwikis, tpl, remaining_text)."""
    cats = CAT_RX.findall(text)
    iws  = IW_RX.findall(text)
    tpls = TPL_RX.findall(text)

    stripped = CAT_RX.sub("", text)
    stripped = IW_RX.sub("", stripped)
    stripped = TPL_RX.sub("", stripped)

    return cats, iws, tpls, stripped.rstrip()

def build_bottom(cats:list[str], iws:list[str], tpls:list[str]) -> str:
    if not (cats or iws or tpls):
        return ""                 # nothing to append
    sec  = ["==Categories==", ""]
    sec += sorted(set(tpls), key=str.casefold)
    sec += sorted(set(cats), key=str.casefold)
    sec += sorted(set(iws),  key=str.casefold)
    return "\n".join(sec) + "\n"

# ── optional start point ────────────────────────────────────────
start_at = None
if len(sys.argv) > 1:
    start_at = sys.argv[1].strip("'\"")
    if not start_at.lower().startswith("category:"):
        start_at = f"Category:{start_at}"

print("Logged in – walking Category namespace")
if start_at:
    print(f"(starting at ≥ {start_at})")

apc = None
passed = not bool(start_at)

while True:
    q = {
        "action":"query", "list":"allpages",
        "apnamespace":14, "aplimit":"max", "format":"json"
    }
    if apc:
        q["apcontinue"] = apc

    batch = site.api(**q)

    for entry in batch["query"]["allpages"]:
        title = entry["title"]
        if not passed and title < start_at:
            continue
        passed = True

        pg = site.pages[title]
        try:
            orig = pg.text()
        except (InvalidPageTitle, APIError):
            print("→", title, " – fetch failed")
            continue

        cats, iws, tpls, body = pull_groups(orig)

        # drop any existing ==Categories== section
        body = HEAD_RX.split(body, maxsplit=1)[0].rstrip()

        new_tail = build_bottom(cats, iws, tpls)
        new_text = body + "\n\n" + new_tail if new_tail else body + "\n"

        if new_text != orig:
            try:
                pg.save(new_text,
                        summary="Bot: move cats/inter-wikis/translated-page to bottom")
                print(f"→ {title}  • updated "
                      f"({len(cats)} cats, {len(iws)} iw, {len(tpls)} tpl)")
            except APIError as e:
                print("→", title, " – save failed:", e.code)
            time.sleep(THROTTLE)
        else:
            print(f"→ {title}  • unchanged")

    apc = batch.get("continue", {}).get("apcontinue")
    if not apc:
        break

print("Finished.")
