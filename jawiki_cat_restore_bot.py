#!/usr/bin/env python3
"""
jawiki_cat_restore_bot.py
=========================
For each English page in pages.txt:

 1. Grab the first [[ja:…]] interwiki link.
 2. Fetch all [[Category:…]] on that JA page.
 3. For each JA category:
    • If a matching local English category exists, add the English page to it.
    • Otherwise:
       – Create Category:<JapaneseName> locally.
       – Tag it with [[Category:Categories generated automatically from jawiki]].
       – Add all other sitelinks from Wikidata as interwikis.
       – Leave an explanatory note.
       – Then add that new category to the English page.
"""

import os, sys, time, urllib.parse
import requests
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
PAGES_FILE = "pages.txt"
SHINTO_URL = "shinto.miraheze.org"
SHINTO_PATH= "/w/"
JA_URL     = "ja.wikipedia.org"
JA_PATH    = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5  # seconds between API calls
GEN_CAT    = "Categories generated automatically from jawiki"
WD_API     = "https://www.wikidata.org/w/api.php"

# ─── LOGIN ──────────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
shinto.login(USERNAME, PASSWORD)
ja     = mwclient.Site(JA_URL, path=JA_PATH)  # read-only

def load_pages(path):
    if not os.path.exists(path):
        print(f"Missing {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def get_first_ja_link(text):
    """Return the page title from the first [[ja:…]] link, or None."""
    import re
    m = re.search(r"\[\[\s*ja:([^|\]]+)", text, re.IGNORECASE)
    if not m:
        return None
    title = m.group(1).strip()
    return urllib.parse.unquote(title).replace("_"," ")

def fetch_ja_categories(title):
    """Return the list of categories (without 'Category:' prefix) on JA page."""
    resp = ja.api(
        action="query",
        format="json",
        prop="categories",
        titles=title,
        cllimit="max"
    )
    pages = resp["query"]["pages"]
    page  = next(iter(pages.values()))
    return [c["title"].split(":",1)[1] for c in page.get("categories",[])]

def get_wd_sitelinks_for_ja_category(ja_cat):
    """
    1) Query pageprops on JA wiki to get the wikibase_item.
    2) Query WD for its sitelinks.
    """
    # 1) get the entity ID
    resp = ja.api(
        action="query",
        format="json",
        prop="pageprops",
        titles=f"Category:{ja_cat}",
        ppprop="wikibase_item"
    )
    pp = next(iter(resp["query"]["pages"].values())).get("pageprops",{})
    qid = pp.get("wikibase_item")
    if not qid:
        return {}
    # 2) fetch sitelinks from WD
    r = requests.get(WD_API, params={
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "format": "json"
    }, timeout=30).json()
    entity = r["entities"].get(qid, {})
    return entity.get("sitelinks", {})

def local_category_exists(name):
    return shinto.pages[f"Category:{name}"].exists

def create_ja_category(ja_cat, eng_page):
    """Create Category:ja_cat with boilerplate + interwikis."""
    title = f"Category:{ja_cat}"
    page  = shinto.pages[title]
    if page.exists:
        return
    sl = get_wd_sitelinks_for_ja_category(ja_cat)
    lines = []
    lines.append(f"[[Category:{GEN_CAT}]]")
    lines.append(f"[[ja:Category:{ja_cat}]]")
    # all other languages
    for code, info in sl.items():
        if not code.endswith("wiki") or code=="jawiki":
            continue
        prefix = code[:-4]
        tgt    = info["title"]
        # strip redundant 'Category:' if present
        if tgt.startswith("Category:"):
            tgt = tgt.split(":",1)[1]
        lines.append(f"[[{prefix}:Category:{tgt}]]")
    lines.append("")
    lines.append(f"This category was automatically created for the Jawiki link [[ja:Category:{ja_cat}]] on page [[{eng_page}]].")
    lines.append("Please move/rename it to its English name in the future.")
    text = "\n".join(lines) + "\n"
    try:
        page.save(text, summary="Bot: auto-create jawiki category")
        print(f"    • Created [[Category:{ja_cat}]]")
    except APIError as e:
        print(f"    ! FAILED to create Category:{ja_cat}: {e.code}")

def add_category_to_eng_page(eng_page, cat_name):
    """Append [[Category:cat_name]] to the English page if missing."""
    page = shinto.pages[eng_page]
    txt  = page.text()
    marker = f"[[Category:{cat_name}]]"
    if marker in txt:
        return
    new = txt.rstrip() + "\n" + marker + "\n"
    try:
        page.save(new, summary=f"Bot: add category {cat_name}")
        print(f"    • Tagged [[{eng_page}]] → {cat_name}")
    except APIError as e:
        print(f"    ! FAILED tagging [[{eng_page}]]: {e.code}")

def main():
    pages = load_pages(PAGES_FILE)
    total = len(pages)

    for idx, eng in enumerate(pages, 1):
        print(f"\n{idx}/{total}: [[{eng}]]")
        pg = shinto.pages[eng]
        if not pg.exists:
            print("  ! page missing; skipping")
            continue

        ja_link = get_first_ja_link(pg.text())
        if not ja_link:
            print("  ! no [[ja:…]] link; skipping")
            continue
        print(f"    → jawiki: {ja_link}")

        try:
            cats = fetch_ja_categories(ja_link)
        except Exception as e:
            print(f"    ! could not fetch JA cats: {e}")
            continue

        print(f"    → {len(cats)} JA categories found")
        for ja_cat in cats:
            # 1) see if WD gives an English sitelink
            sl = get_wd_sitelinks_for_ja_category(ja_cat)
            en_info = sl.get("enwiki")
            if en_info:
                eng_cat = en_info["title"].split(":",1)[-1]
                # if a local Category:EngCat exists, just add
                if local_category_exists(eng_cat):
                    print(f"    ↳ existing local Category:{eng_cat}")
                    add_category_to_eng_page(eng, eng_cat)
                    time.sleep(THROTTLE)
                    continue

            # 2) else create the Japanese-titled category and then add
            print(f"    ↳ creating Category:{ja_cat}")
            create_ja_category(ja_cat, eng)
            add_category_to_eng_page(eng, ja_cat)
            time.sleep(THROTTLE)

    print("\nAll done.")

if __name__=="__main__":
    main()
