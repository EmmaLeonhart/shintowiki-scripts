#!/usr/bin/env python3
"""
zhwiki_cat_restore_bot.py  –  zh-wiki → local category sync (v-2025-05-14)
--------------------------------------------------------------------------

*New in this version* – if `Category:<zh-name>` already exists **and** is a
#REDIRECT to another local category, that target is treated as the confirmed
category and is used on the article; no duplicate zh category is created.

All other logic is the same as the previous release (status-tags,
zh-redirects when we create an EN-named category, inter-wiki lines, etc.)
"""

import os, sys, time, urllib.parse, re, html
from typing import Dict, List, Optional

import requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL   = "shinto.miraheze.org"
SHINTO_PATH  = "/w/"
zh_URL       = "zh.wikipedia.org"
zh_PATH      = "/w/"

USERNAME     = "EmmaBot"
PASSWORD     = "[REDACTED_SECRET_1]"

PAGES_FILE   = "pages.txt"
THROTTLE     = 0.1
WD_API       = "https://www.wikidata.org/w/api.php"

TAG_EXISTING = "Existing categories confirmed with Wikidata zh"
TAG_EN_NEW   = "Categories created from enwiki title"
TAG_zh_NEW   = "Categories created from zhwiki title"
TAG_REDIRECT = "zhwiki redirect categories"

# ─── MW SESSIONS ────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
shinto.login(USERNAME, PASSWORD)
zh     = mwclient.Site(zh_URL, path=zh_PATH)           # read-only

print(f"Logged in to {SHINTO_URL} as {USERNAME}")

# ─── UTILS ──────────────────────────────────────────────────────────
def load_titles(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

ILL_zh_RE = re.compile(r"\[\[\s*zh:([^|\]]+)", re.I)

def first_zh_link(text: str) -> Optional[str]:
    m = ILL_zh_RE.search(text)
    if m:
        return urllib.parse.unquote(m.group(1)).replace("_", " ")
    return None

def zh_categories(title: str) -> List[str]:
    data = zh.api(
        action="query", format="json",
        prop="categories", titles=title,
        clshow="!hidzhn", cllimit="max"
    )
    page = next(iter(data["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in page.get("categories", [])]

def zh_cat_qid(zh_cat: str) -> Optional[str]:
    data = zh.api(
        action="query", format="json",
        prop="pageprops", titles=f"Category:{zh_cat}",
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
    return {cozh[:-4]: info["title"].split(":",1)[-1]
            for cozh,info in sl.items() if cozh.endswith("wiki")}

# ─── CORE HELPERS ───────────────────────────────────────────────────
REDIRECT_RE = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)\]\]", re.I)

def existing_redirect_target(zh_cat: str) -> Optional[str]:
    """If Category:<zh_cat> exists *and* is a redirect, return the target name."""
    pg = shinto.pages[f"Category:{zh_cat}"]
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
        print(f"    ! save failed for {page.name}: {e.cozh}")


# ─── NEW HELPER ────────────────────────────────────────────────────
def append_if_missing(page, lines: List[str], summary: str) -> None:
    """
    Append each line in *lines* to *page* (at the very end) only
    if it is not already present.
    """
    try:
        txt = page.text()
    except Exception:
        return                          # cannot read page, give up

    missing = [ln for ln in lines if ln not in txt]
    if not missing:
        return                          # nothing to add

    new_txt = txt.rstrip() + "\n" + "\n".join(missing) + "\n"
    save_page(page, new_txt, summary)


def ensure_local_category(zh_cat: str,
                          en_title: Optional[str],
                          src_article: str) -> str:
    """
    Make sure a *local* category exists and return its *full* page title,
    handling the special case where a zh-named category already exists as a
    redirect to the proper English-named category.
    """
    # Special-case: zh title exists and redirects → treat that target as confirmed
    redir_target = existing_redirect_target(zh_cat)
    if redir_target:
        print(f"      · zh cat is redirect → using {redir_target}")
        return redir_target

    via_en = bool(en_title)
    cat_name   = en_title or zh_cat
    local_page = shinto.pages[f"Category:{cat_name}"]
    existed    = local_page.exists

    # ---------- build category body ----------
    lines = []
    tag = (TAG_EXISTING if existed
           else TAG_EN_NEW if via_en
           else TAG_zh_NEW)
    lines.append(f"[[Category:{tag}]]")

    # zh link
    lines.append(f"[[zh:Category:{zh_cat}]]")

    # other inter-wikis
    if (qid := zh_cat_qid(zh_cat)):
        for cozh, name in wd_sitelinks(qid).items():
            if cozh in ("zh","en"):  # skip duplicates
                continue
            lines.append(f"[[{cozh}:Category:{name}]]")

    lines.append("")
    lines.append(
        f"This category was {'created' if not existed else 'confirmed'} "
        f"from zh→Wikidata links on [[{src_article}]]."
    )
    body = "\n".join(lines) + "\n"

    # ---------- write / update category page ----------

    if existed:
        # Page already exists → only *append* new metadata lines
        append_if_missing(
            local_page,
            lines,                             # the lines we just built
            "Bot: append category metadata"
        )
    else:
        # Fresh category → create full body
        body = "\n".join(lines) + "\n"
        save_page(local_page, body,
                  "Bot: create category from zh/Wikidata")
        print(f"      · created Category:{cat_name} ({tag})")


    # If we *created* the EN category, also create zh redirect
    if (not existed) and via_en:
        zh_redirect = shinto.pages[f"Category:{zh_cat}"]
        if not zh_redirect.exists:
            red_body = (f"#redirect [[Category:{cat_name}]]\n"
                        f"[[Category:{TAG_REDIRECT}]]\n")
            save_page(zh_redirect, red_body,
                      "Bot: zhwiki-title redirect to EN category")
            print(f"        · created redirect Category:{zh_cat}")

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
        print(f"    ! tagging failed on [[{article}]]: {e.cozh}")

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    arts = load_titles(PAGES_FILE)
    for idx, art in enumerate(arts, 1):
        print(f"\n{idx}/{len(arts)} → [[{art}]]")
        art_pg = shinto.pages[art]
        if not art_pg.exists:
            print("  ! article missing – skipped")
            continue

        zh_link = first_zh_link(art_pg.text())
        if not zh_link:
            print("  ! no zh interwiki – skipped")
            continue
        print(f"    · zhwiki: {zh_link}")

        try:
            zh_cats = zh_categories(zh_link)
        except Exception as e:
            print(f"    ! failed to fetch zh cats: {e}")
            continue
        if not zh_cats:
            print("    · no categories")
            continue
        print(f"    · {len(zh_cats)} categories")

        for zh_cat in zh_cats:
            qid = zh_cat_qid(zh_cat)
            en_name = None
            if qid:
                en_name = wd_sitelinks(qid).get("en")
            if en_name:
                print(f"      ↳ enwiki: {en_name}")
            else:
                print(f"      ↳ (no enwiki)")

            local = ensure_local_category(
                zh_cat=zh_cat,
                en_title=en_name,
                src_article=art
            )
            add_category_to_article(art, local)
            time.sleep(THROTTLE)

    print("\nDone.")

# ─── RUN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
