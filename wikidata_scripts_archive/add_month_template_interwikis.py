#!/usr/bin/env python3
"""
add_month_template_interwikis_v2.py
===================================
Fix for AttributeError on `.page_property` when using **mwclient ≤ 0.10**
----------------------------------------------------------------------------
The rest of the behaviour is identical to the original description:
  * always adds the Persian (fa) template name from the static table
  * additionally adds every sitelink found on the template’s Wikidata item
    (if any) except the local miraheze site
  * never duplicates links that are already present
  * inserts the block of new links just **before** the first <noinclude>
    or, if the template lacks such a block, appends them at EOF.

Run:
    python add_month_template_interwikis_v2.py
"""

API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "EmmaBot"
PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE = 0.4
UA       = {"User-Agent": "islamic-month-interwikis/1.1 (User:EmmaBot)"}

import re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── Persian template map ──────────────────────────────────────────
FA_MAP = {
    "Muharram":        "الگو:محرم",
    "Safar":           "الگو:صفر",
    "Rabi' al-Awwal":  "الگو:ربیع‌الاول",
    "Rabi' al-Thani":  "الگو:ربیع‌الثانی",
    "Jumada al-Awwal": "الگو:جمادی‌الاول",
    "Jumada al-Thani": "الگو:جمادی‌الثانی",
    "Rajab":           "الگو:رجب",
    "Sha'ban":         "الگو:شعبان",
    "Ramadan":         "الگو:رمضان",
    "Shawwal":         "الگو:شوال",
    "Dhu al-Qadah":    "الگو:ذیقعده",
    "Dhu al-Hijjah":   "الگو:ذیحجه",
}

# ─── sessions ─────────────────────────────────────────────────────
up = urllib.parse.urlparse(API_URL)
site = mwclient.Site(up.netloc, path=up.path.rsplit("/api.php",1)[0] + "/")
site.login(USERNAME, PASSWORD)

WD_API = "https://www.wikidata.org/w/api.php"

# ─── regex helpers ────────────────────────────────────────────────
IW_RX = re.compile(r"^\[\[([a-z\-]{2,12}):", re.I | re.M)


def existing_langs(text: str) -> set[str]:
    return {m.group(1).lower() for m in IW_RX.finditer(text)}


def wikibase_item_for(page_title: str) -> str | None:
    """Return the Wikidata Qid for *page_title* (or None)."""
    data = site.api(
        action="query", prop="pageprops", titles=page_title,
        ppprop="wikibase_item", format="json"
    )
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops", {}).get("wikibase_item")


def wd_sitelinks(qid: str) -> dict[str, str]:
    if not qid:
        return {}
    j = requests.get(
        WD_API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "format": "json",
        },
        headers=UA,
        timeout=10,
    ).json()
    sl = j.get("entities", {}).get(qid, {}).get("sitelinks", {})
    return {code[:-4]: data["title"] for code, data in sl.items()}


def insert_links(text: str, links: list[str]) -> str:
    block = "\n".join(links) + "\n"
    pos = text.find("<noinclude")
    if pos == -1:
        return text.rstrip() + "\n" + block
    return text[:pos] + block + text[pos:]

# ─── iterate templates ────────────────────────────────────────────
updated = 0
cont    = None
while True:
    resp = site.api(
        action="query", list="allpages", apnamespace=10, apprefix="Islamic ",
        aplimit="max", apcontinue=cont or "", format="json"
    )
    for entry in resp["query"]["allpages"]:
        title = entry["title"]                # Template:Islamic …
        try:
            pg = site.pages[title]
        except InvalidPageTitle:
            continue
        month = title.rsplit(" ", 1)[-1]

        needed: list[tuple[str,str]] = []
        if month in FA_MAP:
            needed.append(("fa", FA_MAP[month]))

        qid = wikibase_item_for(title)
        if qid:
            for lang, name in wd_sitelinks(qid).items():
                if lang != "shn":            # local miraheze language code
                    needed.append((lang, name))

        if not needed:
            continue

        have = existing_langs(pg.text())
        add  = [f"[[{lang}:{name}]]" for lang, name in needed
                if lang.lower() not in have]
        if not add:
            continue

        new_text = insert_links(pg.text(), add)
        try:
            pg.save(new_text, summary="Bot: add inter-wiki links (fa + WD)")
            print(" •", title)
            updated += 1
        except APIError as e:
            print("   ! save failed", title, e.code)
        time.sleep(THROTTLE)

    if "continue" in resp:
        cont = resp["continue"].get("apcontinue")
    else:
        break

print(f"Done – {updated} templates updated.")
