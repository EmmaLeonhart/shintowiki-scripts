#!/usr/bin/env python3
"""
fix_islamic_template_ills_v4.py
===============================

• Works on every page in  [[Category:Islamic calendar templates]].
• Reads the *authoritative* {{ill}} lines from
  [[List_of_days_of_the_Islamic_Calendar]] and builds a mapping:
      "Dhu al-Hijjah 30"  →  [("ms","30 Zulhijah"), ("ar","30 ذو الحجة"), …]

• Any {{ill|…}} in the template pages is replaced by

     {{ill|Month N|lang1|title1|lang2|title2|…|lt=Whatever}}

  – ONLY “lt=” is kept from the old call; every other named / numbered
    parameter is discarded.

• Robust first-parameter detection:
    – skips empty items after the first “|”
    – collapses internal whitespace
    – if the first positional parameter is *only one word*, tries the
      **next** parameter as part of a split “D|hu al-Hijjah 30”.
    – finally validates with a regex that matches the 12 month names
      + 1-30.

You can re-run as often as you like; already-fixed pages are left
unchanged.

-------------------------------------------------------------------
"""

API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
MASTER    = "List_of_days_of_the_Islamic_Calendar"
TEMPL_CAT = "Islamic calendar templates"
THROTTLE  = 0.5    # seconds

import re, time, urllib.parse, mwclient
from mwclient.errors import APIError, InvalidPageTitle

u    = urllib.parse.urlparse(API_URL)
site = mwclient.Site(u.netloc, path=u.path.rsplit("/api.php",1)[0]+"/")
site.login(USERNAME, PASSWORD)

# ─── month name list / date matcher ────────────────────────────────
MONTHS = [
    "Muharram", "Safar", "Rabi' al-Awwal", "Rabi' al-Thani",
    "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhu al-Qadah", "Dhu al-Hijjah"
]
DATE_RX = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in MONTHS) + r")\s+([1-9]|[12]\d|30)\b",
    re.I
)

ILL_RX = re.compile(r"\{\{ill\s*\|(?P<body>[^{}]+?)\}\}", re.S | re.I)

# ─── 1) build “Month N” → lang/title list mapping from master page ─
mapping = {}
for m in ILL_RX.finditer(site.pages[MASTER].text()):
    body = m.group("body")
    mo   = DATE_RX.search(body)
    if not mo:
        continue
    key = f"{mo.group(1)} {mo.group(2)}"
    parts = body.split("|")
    # take pairs lang,title after the (first) date
    lang_pairs = []
    i = 0
    while i < len(parts):
        p = parts[i].strip()
        if p.lower().strip() in ("lt", "day", "month"):
            i += 2             # skip key=value
        elif len(p) == 2 and i+1 < len(parts):   # lang-code
            lang_pairs.append((p, parts[i+1].strip()))
            i += 2
        else:
            i += 1
    if lang_pairs:
        mapping[key] = lang_pairs

print(f"[info] extracted {len(mapping):,} entries from master list")

# ─── 2) helper that finds/cleans parameter-1 in *any* broken {{ill}} ─
def canonical_key(raw_body: str) -> tuple[str, str|None]:
    """
    Return (month-N key, lt_value_or_None) or ("", None) if no date found.
    """
    # split on | but keep empties
    parts = raw_body.split("|")
    idx = 0
    while idx < len(parts) and not parts[idx].strip():
        idx += 1
    if idx >= len(parts):
        return "", None

    first = parts[idx].strip()
    # 1-word first param? try to merge with next if that yields a date
    if idx+1 < len(parts) and " " not in first:
        probe = f"{first} {parts[idx+1].strip()}"
        if DATE_RX.fullmatch(probe):
            first = probe
            idx += 1

    mo = DATE_RX.fullmatch(first)
    if not mo:
        return "", None
    key = mo.group(0)                       # canonical “Month N”

    # scan for lt=
    lt = None
    for item in parts[idx+1:]:
        if "=" in item:
            k, v = item.split("=", 1)
            if k.strip().lower() == "lt":
                lt = v.strip()
                break
    return key, lt

# ─── 3) function to rewrite one {{ill|…}} ──────────────────────────
def rewrite(match: re.Match) -> str:
    key, lt = canonical_key(match.group("body"))
    if key not in mapping:
        return match.group(0)               # leave untouched

    segs = [key]
    for lang, title in mapping[key]:
        segs += [lang, title]
    if lt:
        segs.append(f"lt={lt}")
    return "{{ill|" + "|".join(segs) + "}}"

# ─── 4) walk every template page in the category ───────────────────
edited = 0
cmc = None
while True:
    q = site.api(action="query", list="categorymembers",
                 cmtitle=f"Category:{TEMPL_CAT}", cmtype="page",
                 cmlimit="max", cmcontinue=cmc or "", format="json")
    for ent in q["query"]["categorymembers"]:
        try:
            page = site.pages[ent["title"]]
        except InvalidPageTitle:
            continue
        old = page.text()
        new = ILL_RX.sub(rewrite, old)
        if new != old:
            try:
                page.save(new, summary="Bot: fix {{ill}} date-links (month/day)")
                print(" • fixed", page.name)
                edited += 1
            except APIError as e:
                print("   ! save failed on", page.name, e.code)
            time.sleep(THROTTLE)
    if "continue" in q:
        cmc = q["continue"]["cmcontinue"]
    else:
        break

print(f"\nCompleted – {edited} pages rewritten.")
