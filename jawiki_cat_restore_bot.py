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

def ensure_local_category(cat_name: str, ja_cat: str, eng_page: str, via_en: bool) -> str:
    """
    Ensure Category:cat_name exists locally with exactly one marker:
      - EXISTING_CAT    if the page already existed
      - EN_CREATED      if created via an English sitelink
      - JA_CREATED      if created via the Ja interwiki

    Never overwrite if one of those markers is already present.
    Returns the local category title (e.g. "Category:Foo").
    """
    full = f"Category:{cat_name}"
    pg = site.pages[full]

    # 1) If it already has one of our markers, skip entirely
    text = pg.text() if pg.exists else ""
    for marker in (EXISTING_CAT, EN_CREATED, JA_CREATED):
        if f"[[Category:{marker}]]" in text:
            print(f"    • already tagged ({marker}), skipping")
            return full

    existed_before = pg.exists

    # 2) Choose the right marker
    if not existed_before:
        tag = EN_CREATED if via_en else JA_CREATED
    else:
        tag = EXISTING_CAT

    # 3) Build new page content
    lines: list[str] = []
    lines.append(f"[[Category:{tag}]]")
    lines.append(f"[[ja:Category:{ja_cat}]]")

    # 4) Pull in any other sitelinks from Wikidata (if you have a QID lookup)
    #    (assumes a function get_sitelinks(qid) -> dict[lang, title])
    qid = get_qid_for_category(ja_cat)  # or however you retrieve it
    if qid:
        for lang, link in get_sitelinks(qid).items():
            if lang not in ("en", "ja"):
                lines.append(f"[[{lang}:{link}]]")

    lines.append("")  # blank line before footer
    lines.append(
        f"This category was "
        f"{'created from' if not existed_before else 'confirmed via'} "
        f"{'enwiki sitelink' if via_en else 'jawiki link'} "
        f"[[ja:Category:{ja_cat}]] on [[{eng_page}]]."
    )

    body = "\n".join(lines) + "\n"

    # 5) Save the new or updated category page
    try:
        pg.save(body, summary="Bot: sync category from jawiki↔Wikidata")
        action = "Created" if not existed_before else "Updated"
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
