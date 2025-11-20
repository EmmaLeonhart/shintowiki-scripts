#!/usr/bin/env python3
"""
category_enwiki_sync_bot.py
===========================
Synchronise local category names with the English Wikipedia title derived via
Wikidata (using either the jawiki or dewiki sitelink as pivot).

Steps per category listed in *categories.txt*:

1. **Determine enwiki title**
   ────────────────
   • Scan the page for `[[ja:Category:…]]` and `[[de:Category:…]]` links.
   • For the *first* link found, fetch its Wikidata item and read the
     *enwiki* sitelink (if any). If none → category is skipped.

2. **Append the enwiki interwiki** (`[[en:Category:<Title>]]`) to the bottom of
   the local category page when missing.

3. **Compare names**
   • If the local category *already* matches `<Title>`, append the tracking
     tag `[[Category:confirmed enwiki categories]]` (if not present).
   • Otherwise, **rename** the category to the English title and update **all
     members** so they categorise under the new name. The old category page is
     left as a redirect.

Edit flow when renaming
-----------------------
```
    Category:Foo (old)
        ├─ move → Category:Bar (new, reason: "Bot: rename to enwiki name")
        └─ iterate members
             – replace "[[Category:Foo…]]" → "[[Category:Bar…]]"
```
Each member edit gets the summary:
    *"Bot: update category link to [[Category:Bar]]"*

Configuration
-------------
Adjust USERNAME/PASSWORD and other constants below. Category titles (without the
"Category:" prefix) go into **categories.txt** – one per line.
"""

import os, sys, re, time, urllib.parse, requests, mwclient
from typing import List, Optional
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
CATS_FILE  = "categories.txt"
THROTTLE   = 0.4    # seconds between edits

API_WD     = "https://www.wikidata.org/w/api.php"

LANG_WIKIS = {
    "ja": mwclient.Site("ja.wikipedia.org", path="/w/"),
    "de": mwclient.Site("de.wikipedia.org", path="/w/"),
}

# ─── UTILITY -------------------------------------------------------

def load_cat_titles(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


IW_RE = re.compile(r"\[\[\s*(ja|de)\s*:\s*Category:([^\]|]+)", re.I)


def api_json(url: str, params):
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def wikidata_qid(category_title: str, lang: str) -> Optional[str]:
    site = LANG_WIKIS[lang]
    try:
        data = site.api(
            action="query", format="json",
            prop="pageprops", titles=f"Category:{category_title}",
            ppprop="wikibase_item",
        )
        props = next(iter(data["query"]["pages"].values())).get("pageprops", {})
        return props.get("wikibase_item")
    except Exception:
        return None


def enwiki_from_qid(qid: str) -> Optional[str]:
    if not qid:
        return None
    data = api_json(API_WD, {
        "action": "wbgetentities", "format": "json",
        "ids": qid, "props": "sitelinks", "sitefilter": "enwiki",
    })
    sl = data.get("entities", {}).get(qid, {}).get("sitelinks", {}).get("enwiki")
    if not sl:
        return None
    return sl["title"].split(":", 1)[-1]  # strip namespace if present

# ─── MEMBER UPDATE -------------------------------------------------

def update_member_categories(page: mwclient.page.Page, old: str, new: str):
    txt = page.text()
    # replace [[Category:Old]] or [[Category:Old|sort]] variants
    new_txt = re.sub(rf"\[\[Category:{re.escape(old)}(\|[^\]]*)?\]\]",
                     rf"[[Category:{new}\1]]", txt, flags=re.I)
    if new_txt != txt:
        try:
            page.save(new_txt,
                      summary=f"Bot: update category link to [[Category:{new}]]")
            print(f"          · updated [[{page.name}]]")
            return True
        except APIError as e:
            print(f"          ! save failed on {page.name}: {e.code}")
    return False

# ─── MAIN ----------------------------------------------------------

def process_category(site: mwclient.Site, cat_title: str):
    full_title = f"Category:{cat_title}"
    cat_page   = site.pages[full_title]
    if not cat_page.exists:
        print("  ! category page missing – skipped")
        return

    text = cat_page.text()
    m = IW_RE.search(text)
    if not m:
        print("  ! no ja/de interwiki – skipped")
        return

    lang, foreign_cat = m.group(1).lower(), m.group(2).strip()
    qid = wikidata_qid(foreign_cat, lang)
    en_title = enwiki_from_qid(qid)
    if not en_title:
        print("  ! no enwiki sitelink – skipped")
        return

    print(f"    · enwiki title: {en_title}")

    # 1) ensure enwiki interwiki present
    en_iw = f"[[en:Category:{en_title}]]"
    if en_iw not in text:
        cat_page.save(text.rstrip() + "\n" + en_iw + "\n",
                       summary="Bot: add enwiki interwiki")
        text += "\n" + en_iw + "\n"
        print("      · en interwiki appended")

    local_name = cat_title.replace("_", " ")
    if local_name.lower() == en_title.lower():
        # same name → tag confirmed
        tag = "[[Category:confirmed enwiki categories]]"
        if tag not in text:
            cat_page.save(text.rstrip() + "\n" + tag + "\n",
                           summary="Bot: mark confirmed enwiki category")
            print("      · tagged as confirmed")
        else:
            print("      · already tagged confirmed")
        return

    # 2) names differ → move category
    new_full = f"Category:{en_title}"
    print(f"      · renaming category → [[{new_full}]]")
    try:
        cat_page.move(new_full,
                      reason="Bot: rename to enwiki category name",
                      movetalk=True, noredirect=False)
    except APIError as e:
        print(f"      ! move failed: {e.code}")
        return

    # 3) update members
    old_name = local_name
    new_name = en_title
    moved_cat = site.categories[new_name]
    before = len(list(site.categories[old_name].members()))
    print(f"      · processing {before} members")
    for mem in site.categories[old_name].members():
        update_member_categories(mem, old_name, new_name)
        time.sleep(THROTTLE)
    after = len(list(site.categories[old_name].members()))
    print(f"      · remaining members in old cat: {after}\n")

# ─── RUNNER --------------------------------------------------------

def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    cats = load_cat_titles(CATS_FILE)
    for idx, title in enumerate(cats, 1):
        print(f"{idx}/{len(cats)} → Category:{title}")
        process_category(site, title)
        time.sleep(THROTTLE)

    print("\nDone.")


if __name__ == "__main__":
    main()
