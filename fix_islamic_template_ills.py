#!/usr/bin/env python3
"""
fix_islamic_template_ills.py  –  v2
-----------------------------------

• collapses any line-breaks / multiple spaces inside the *first* parameter  
• discards **all** named parameters except an optional  lt=
"""

# ── login / constants ──────────────────────────────────────────────
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE = 0.4

MASTER_PAGE = "List_of_days_of_the_Islamic_Calendar"
TARGET_CAT  = "Islamic calendar templates"
# ------------------------------------------------------------------

import re, time, urllib.parse, mwclient
from mwclient.errors import APIError

u   = urllib.parse.urlparse(API_URL)
site = mwclient.Site(u.netloc, path=u.path.rsplit("/api.php", 1)[0] + "/")
site.login(USERNAME, PASSWORD)

ILL_RX = re.compile(r"\{\{ill\s*\|(?P<body>[^{}]+?)\}\}", re.I | re.S)

# ───────────────────────────────────────────────────────────────────
# 1) Build authoritative mapping  EN-title → [(lang,title)...]
# ───────────────────────────────────────────────────────────────────
def _parse_params(raw: str):
    """Return (param1, lt_or_None, list_of_pairs)."""
    parts = [p.strip() for p in raw.split("|")]
    # join lines inside parameter-1 and collapse whitespace
    p1 = re.sub(r"\s+", " ", parts[0])

    lt  = None
    pairs = []
    i = 1
    while i < len(parts):
        if "=" in parts[i]:
            key, val = parts[i].split("=", 1)
            if key.strip().lower() == "lt":
                lt = val.strip()
            # ignore every other key=value
            i += 1
        elif i + 1 < len(parts):
            pairs.append((parts[i], parts[i+1]))
            i += 2
        else:
            break
    return p1, lt, pairs

mapping = {}
for m in ILL_RX.finditer(site.pages[MASTER_PAGE].text()):
    p1, _, pairs = _parse_params(m.group("body"))
    mapping[p1] = pairs

print(f"[mapping] {len(mapping):,} calendar day names recorded")

# ───────────────────────────────────────────────────────────────────
# 2) Template-rewriter
# ───────────────────────────────────────────────────────────────────
def rewrite_ill(match: re.Match) -> str:
    p1, lt, _ = _parse_params(match.group("body"))
    if p1 not in mapping:
        return match.group(0)      # not a calendar-day, leave untouched

    pieces = [p1]
    for lang, title in mapping[p1]:
        pieces += [lang.strip(), title.strip()]
    if lt:
        pieces.append(f"lt={lt.strip()}")

    return "{{ill|" + "|".join(pieces) + "}}"

# ───────────────────────────────────────────────────────────────────
# 3) Walk the ‘Islamic calendar templates’ category
# ───────────────────────────────────────────────────────────────────
edited = 0
cmc = None
while True:
    batch = site.api(action="query", list="categorymembers",
                     cmtitle=f"Category:{TARGET_CAT}", cmtype="page",
                     cmlimit="max", cmcontinue=cmc or "", format="json")
    for ent in batch["query"]["categorymembers"]:
        page = site.pages[ent["title"]]
        old  = page.text()
        new  = ILL_RX.sub(rewrite_ill, old)
        if new != old:
            try:
                page.save(new, summary="Bot: normalise {{ill}} inter-wiki list")
                print(" • updated", page.name)
                edited += 1
            except APIError as e:
                print("   ! save failed on", page.name, e.code)
            time.sleep(THROTTLE)
    if "continue" in batch:
        cmc = batch["continue"]["cmcontinue"]
    else:
        break

print(f"\nDone – {edited} template pages corrected.")
