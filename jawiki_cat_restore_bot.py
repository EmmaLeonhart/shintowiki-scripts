#!/usr/bin/env python3
"""
jawiki_cat_restore_bot.py  –  JA-wiki → local category sync (v-2025-05-14)
--------------------------------------------------------------------------

*New in this version* – if `Category:<JA-name>` already exists **and** is a
#REDIRECT to another local category, that target is treated as the confirmed
category and is used on the article; no duplicate JA category is created.

All other logic is the same as the previous release (status-tags,
JA-redirects when we create an EN-named category, inter-wiki lines, etc.)
"""

import os, sys, time, urllib.parse, re, html
from typing import Dict, List, Optional

import requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL   = "shinto.miraheze.org"
SHINTO_PATH  = "/w/"
JA_URL       = "ja.wikipedia.org"
JA_PATH      = "/w/"

USERNAME     = "Immanuelle"
PASSWORD     = "[REDACTED_SECRET_1]"

PAGES_FILE   = "pages.txt"
THROTTLE     = 0.5
WD_API       = "https://www.wikidata.org/w/api.php"

TAG_EXISTING = "Existing categories confirmed with Wikidata"
TAG_EN_NEW   = "Categories created from enwiki title"
TAG_JA_NEW   = "Categories created from jawiki title"
TAG_REDIRECT = "jawiki redirect categories"

# ─── MW SESSIONS ────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
shinto.login(USERNAME, PASSWORD)
ja     = mwclient.Site(JA_URL, path=JA_PATH)           # read-only

print(f"Logged in to {SHINTO_URL} as {USERNAME}")

# ─── UTILS ──────────────────────────────────────────────────────────
def load_titles(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

ILL_JA_RE = re.compile(r"\[\[\s*ja:([^|\]]+)", re.I)

def first_ja_link(text: str) -> Optional[str]:
    m = ILL_JA_RE.search(text)
    if m:
        return urllib.parse.unquote(m.group(1)).replace("_", " ")
    return None

def ja_categories(title: str) -> List[str]:
    data = ja.api(
        action="query", format="json",
        prop="categories", titles=title,
        clshow="!hidden", cllimit="max"
    )
    page = next(iter(data["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in page.get("categories", [])]

def ja_cat_qid(ja_cat: str) -> Optional[str]:
    data = ja.api(
        action="query", format="json",
        prop="pageprops", titles=f"Category:{ja_cat}",
        ppprop="wikibase_item"
    )
    props = next(iter(data["query"]["pages"].values())).get("pageprops", {})
    return props.get("wikibase_item")

def wd_sitelinks(qid: str) -> Dict[str,str]:
    if not qid:
        return {}
    j = requests.get(WD_API, params={
        "action":"wbgetentities","format":"json",
        "ids":qid,"props":"sitelinks"
    }, timeout=30).json()
    sl = j.get("entities",{}).get(qid,{}).get("sitelinks",{})
    return {code[:-4]: info["title"].split(":",1)[-1]
            for code,info in sl.items() if code.endswith("wiki")}

# ─── CORE HELPERS ───────────────────────────────────────────────────
REDIRECT_RE = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)\]\]", re.I)

def existing_redirect_target(ja_cat: str) -> Optional[str]:
    """If Category:<ja_cat> exists *and* is a redirect, return the target name."""
    pg = shinto.pages[f"Category:{ja_cat}"]
    if not pg.exists:
        return None
    try:
        txt = pg.text().strip()
    except Exception:
        return None
    m = REDIRECT_RE.match(txt)
    if m:
        return f"Category:{m.group(1).strip()}"
    return None

def save_page(page, body, summary):
    try:
        page.save(body, summary=summary)
    except APIError as e:
        print(f"    ! save failed for {page.name}: {e.code}")

def ensure_local_category(ja_cat: str,
                          en_title: Optional[str],
                          src_article: str) -> str:
    """
    Make sure a *local* category exists and return its *full* page title,
    handling the special case where a JA-named category already exists as a
    redirect to the proper English-named category.
    """
    # Special-case: JA title exists and redirects → treat that target as confirmed
    redir_target = existing_redirect_target(ja_cat)
    if redir_target:
        print(f"      · JA cat is redirect → using {redir_target}")
        return redir_target

    via_en = bool(en_title)
    cat_name   = en_title or ja_cat
    local_page = shinto.pages[f"Category:{cat_name}"]
    existed    = local_page.exists

    # ---------- build category body ----------
    lines = []
    tag = (TAG_EXISTING if existed
           else TAG_EN_NEW if via_en
           else TAG_JA_NEW)
    lines.append(f"[[Category:{tag}]]")

    # ja link
    lines.append(f"[[ja:Category:{ja_cat}]]")

    # other inter-wikis
    if (qid := ja_cat_qid(ja_cat)):
        for code, name in wd_sitelinks(qid).items():
            if code in ("ja","en"):  # skip duplicates
                continue
            lines.append(f"[[{code}:Category:{name}]]")

    lines.append("")
    lines.append(
        f"This category was {'created' if not existed else 'confirmed'} "
        f"from JA→Wikidata links on [[{src_article}]]."
    )
    body = "\n".join(lines) + "\n"

    if existed:
        save_page(local_page, body, "Bot: update category metadata")
    else:
        save_page(local_page, body, "Bot: create category from JA/Wikidata")
        print(f"      · created Category:{cat_name} ({tag})")

    # If we *created* the EN category, also create JA redirect
    if (not existed) and via_en:
        ja_redirect = shinto.pages[f"Category:{ja_cat}"]
        if not ja_redirect.exists:
            red_body = (f"#redirect [[Category:{cat_name}]]\n"
                        f"[[Category:{TAG_REDIRECT}]]\n")
            save_page(ja_redirect, red_body,
                      "Bot: jawiki-title redirect to EN category")
            print(f"        · created redirect Category:{ja_cat}")

    return local_page.name

def add_category_to_article(article: str, cat_full: str):
    pg = shinto.pages[article]
    marker = f"[[{cat_full}]]"
    txt = pg.text()
    if marker in txt:
        return
    new = txt.rstrip() + "\n" + marker + "\n"
    try:
        pg.save(new, summary=f"Bot: add category {cat_full}")
        print(f"      · tagged [[{article}]]")
    except APIError as e:
        print(f"    ! tagging failed on [[{article}]]: {e.code}")

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    arts = load_titles(PAGES_FILE)
    for idx, art in enumerate(arts, 1):
        print(f"\n{idx}/{len(arts)} → [[{art}]]")
        art_pg = shinto.pages[art]
        if not art_pg.exists:
            print("  ! article missing – skipped")
            continue

        ja_link = first_ja_link(art_pg.text())
        if not ja_link:
            print("  ! no ja interwiki – skipped")
            continue
        print(f"    · jawiki: {ja_link}")

        try:
            ja_cats = ja_categories(ja_link)
        except Exception as e:
            print(f"    ! failed to fetch JA cats: {e}")
            continue
        if not ja_cats:
            print("    · no categories")
            continue
        print(f"    · {len(ja_cats)} categories")

        for ja_cat in ja_cats:
            qid = ja_cat_qid(ja_cat)
            en_name = None
            if qid:
                en_name = wd_sitelinks(qid).get("en")
            if en_name:
                print(f"      ↳ enwiki: {en_name}")
            else:
                print(f"      ↳ (no enwiki)")

            local = ensure_local_category(
                ja_cat=ja_cat,
                en_title=en_name,
                src_article=art
            )
            add_category_to_article(art, local)
            time.sleep(THROTTLE)

    print("\nDone.")

# ─── RUN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
