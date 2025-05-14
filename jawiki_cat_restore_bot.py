#!/usr/bin/env python3
"""
jawiki_cat_restore_bot.py
=========================
For each English page in pages.txt:

 1. Grab the first [[ja:…]] interwiki link.
 2. Fetch all [[Category:…]] on that JA page.
 3. For each JA category:
    • If Wikidata has an English sitelink:
       – Ensure local Category:<EnglishName> exists.
       – Tag it exactly [[Category:Categories created from enwiki title]]
         if we created it now, or
                [[Category:Existing categories confirmed with Wikidata]]
         if it already existed.
    • Otherwise:
       – Ensure local Category:<JapaneseName> exists.
       – Tag it exactly [[Category:Categories created from jawiki title]].
    • In all cases:
       – Add the other sitelinks (JA + any others from Wikidata).
       – At the bottom leave a one-line note pointing back to the source.
    • Finally, add that category to the English page.
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
WD_API     = "https://www.wikidata.org/w/api.php"

# the three status‐categories
EXISTING_CAT = "Existing categories confirmed with Wikidata"
EN_CREATED  = "Categories created from enwiki title"
JA_CREATED  = "Categories created from jawiki title"

# ─── LOGIN ──────────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
shinto.login(USERNAME, PASSWORD)
ja     = mwclient.Site(JA_URL, path=JA_PATH)  # read-only mirror

def load_pages(path):
    if not os.path.exists(path):
        print(f"Missing {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def get_first_ja_link(text):
    import re
    m = re.search(r"\[\[\s*ja:([^|\]]+)", text, re.IGNORECASE)
    return urllib.parse.unquote(m.group(1)).replace("_"," ") if m else None

def fetch_ja_categories(title):
    resp = ja.api(
        action="query", format="json",
        prop="categories", titles=title,
        cllimit="max"
    )
    pg = next(iter(resp["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in pg.get("categories",[])]

def lookup_wd_item_for_cat(ja_cat):
    resp = ja.api(
        action="query", format="json",
        prop="pageprops", titles=f"Category:{ja_cat}",
        ppprop="wikibase_item"
    )
    props = next(iter(resp["query"]["pages"].values())).get("pageprops",{})
    return props.get("wikibase_item")

def get_wd_sitelinks(qid):
    r = requests.get(WD_API, params={
        "action":"wbgetentities","ids":qid,
        "props":"sitelinks","format":"json"
    }, timeout=30).json()
    return r.get("entities",{}).get(qid,{}).get("sitelinks",{})

def ensure_local_category(cat_name, ja_cat, eng_page, via_en):
    """
    Ensure Category:cat_name exists locally.
    Tag it with exactly one of EXISTING_CAT, EN_CREATED or JA_CREATED.
    Return the full local page name 'Category:cat_name'.
    """
    full = f"Category:{cat_name}"
    pg   = shinto.pages[full]
    existed = pg.exists

    # build interwiki + note
    lines = []
    # pick the correct tag
    if existed:
        tag = EXISTING_CAT
    else:
        tag = EN_CREATED if via_en else JA_CREATED
    lines.append(f"[[Category:{tag}]]")

    # always link back to jawiki
    lines.append(f"[[ja:Category:{ja_cat}]]")

    # add all other sitelinks from Wikidata if available
    qid = lookup_wd_item_for_cat(ja_cat)
    if qid:
        for code, info in get_wd_sitelinks(qid).items():
            if code=="jawiki": continue
            if not code.endswith("wiki"): continue
            prefix = code[:-4]
            tgt    = info["title"].split(":",1)[-1]
            lines.append(f"[[{prefix}:Category:{tgt}]]")

    # explanatory footer
    lines.append("")
    lines.append(
        f"This category was {'created from' if not existed else 'confirmed via'} "
        f"{'enwiki sitelink' if via_en else 'jawiki link'} [[ja:Category:{ja_cat}]] "
        f"found on [[{eng_page}]]."
    )
    body = "\n".join(lines) + "\n"

    # save or update
    try:
        pg.save(body, summary="Bot: sync category from jawiki↔Wikidata")
        action = "Updated" if existed else "Created"
        print(f"    • {action} {full} (tagged {tag})")
    except APIError as e:
        print(f"    ! failed saving {full}: {e.code}")

    return full

def add_category_to_page(page, cat_full):
    pg = shinto.pages[page]
    mark = f"[[{cat_full}]]"
    text = pg.text()
    if mark not in text:
        new = text.rstrip() + "\n" + mark + "\n"
        try:
            pg.save(new, summary=f"Bot: add category {cat_full}")
            print(f"    • Tagged [[{page}]] → {cat_full}")
        except APIError as e:
            print(f"    ! failed tagging [[{page}]]: {e.code}")

def main():
    pages = load_pages(PAGES_FILE)
    total = len(pages)

    for idx, eng in enumerate(pages, 1):
        print(f"\n{idx}/{total}: [[{eng}]]")
        pg = shinto.pages[eng]
        if not pg.exists:
            print("  ! missing; skip")
            continue

        ja_link = get_first_ja_link(pg.text())
        if not ja_link:
            print("  ! no [[ja:…]]; skip")
            continue
        print(f"    → jawiki: {ja_link}")

        try:
            cats = fetch_ja_categories(ja_link)
        except Exception as e:
            print(f"    ! failed fetch JA cats: {e}")
            continue

        print(f"    → {len(cats)} categories")
        for ja_cat in cats:
            # see if Wikidata gives an English sitelink
            qid = lookup_wd_item_for_cat(ja_cat)
            enlink = None
            if qid:
                sls = get_wd_sitelinks(qid)
                enlink = sls.get("enwiki",{}).get("title")
            if enlink:
                eng_cat = enlink.split(":",1)[-1]
                print(f"    ↳ EN: {eng_cat}")
                local = ensure_local_category(eng_cat, ja_cat, eng, via_en=True)
            else:
                print(f"    ↳ no EN; use JA: {ja_cat}")
                local = ensure_local_category(ja_cat, ja_cat, eng, via_en=False)

            add_category_to_page(eng, local)
            time.sleep(THROTTLE)

    print("\nDone.")

if __name__=="__main__":
    main()
