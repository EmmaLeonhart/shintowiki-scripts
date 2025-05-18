#!/usr/bin/env python3
"""
jawiki_cat_restore_bot_T2.py  –  JA-wiki → local category sync  (v-2025-05-17)

Variant that **preserves existing category content** and always adds
[[Category:Tier 2 Categories]] to every category it edits or creates.
"""

import os, sys, time, urllib.parse, re, html, requests, mwclient
from typing import Dict, List, Optional
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL   = "shinto.miraheze.org"
SHINTO_PATH  = "/w/"
JA_URL       = "ja.wikipedia.org"
JA_PATH      = "/w/"

USERNAME     = "Immanuelle"
PASSWORD     = "[REDACTED_SECRET_1]"

PAGES_FILE   = "pages.txt"
THROTTLE     = 0.1
WD_API       = "https://www.wikidata.org/w/api.php"

TAG_EXISTING = "Existing categories confirmed with Wikidata"
TAG_EN_NEW   = "Categories created from enwiki title"
TAG_JA_NEW   = "Categories created from jawiki title"
TAG_REDIRECT = "jawiki redirect categories"
TIER2_CAT    = "Tier 2 Categories"            # <- new

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

# ――― helpers that **preserve** existing text ―――
def ensure_line(body: str, line: str) -> str:
    """Append *line* (with trailing newline) if it isn’t already present."""
    if line not in body:
        if not body.endswith("\n"):
            body += "\n"
        body += line + "\n"
    return body

def save_if_changed(page, new_text: str, summary: str):
    try:
        if new_text != page.text():
            page.save(new_text, summary=summary)
    except APIError as e:
        print(f"    ! save failed for {page.name}: {e.code}")

def ensure_local_category(ja_cat: str,
                          en_title: Optional[str],
                          src_article: str) -> str:
    """
    Guarantee a *local* category exists and return its full page title,
    without deleting/replacing whatever text is already there.
    Also appends [[Category:Tier 2 Categories]].
    """
    # Case 1: JA-named category already redirects to final target
    redir_target = existing_redirect_target(ja_cat)
    if redir_target:
        print(f"      · JA cat is redirect → using {redir_target}")
        target_page = shinto.pages[redir_target]
        # make sure the redirect target itself is Tier-2-tagged
        body = target_page.text()
        body = ensure_line(body, f"[[Category:{TIER2_CAT}]]")
        save_if_changed(target_page, body,
                        "Bot: ensure Tier-2 tag (existing redirect target)")
        return redir_target

    via_en       = bool(en_title)
    cat_name     = en_title or ja_cat
    local_page   = shinto.pages[f"Category:{cat_name}"]
    existed      = local_page.exists
    tag          = (TAG_EXISTING if existed
                    else TAG_EN_NEW if via_en
                    else TAG_JA_NEW)

    if existed:
        # ---- read current text and *append* anything missing ----
        body = local_page.text()
        body = ensure_line(body, f"[[Category:{tag}]]")
        body = ensure_line(body, f"[[Category:{TIER2_CAT}]]")
        body = ensure_line(body, f"[[ja:Category:{ja_cat}]]")

        if (qid := ja_cat_qid(ja_cat)):
            for code, name in wd_sitelinks(qid).items():
                if code in ("ja","en"):
                    continue
                body = ensure_line(body, f"[[{code}:Category:{name}]]")

        save_if_changed(local_page, body, "Bot: append metadata & Tier-2 tag")

    else:
        # ---- create fresh category ----
        lines = [
            f"[[Category:{tag}]]",
            f"[[Category:{TIER2_CAT}]]",
            f"[[ja:Category:{ja_cat}]]"
        ]

        if (qid := ja_cat_qid(ja_cat)):
            for code, name in wd_sitelinks(qid).items():
                if code in ("ja","en"):
                    continue
                lines.append(f"[[{code}:Category:{name}]]")

        lines.append("")
        lines.append(
            f"This category was created from JA→Wikidata links on [[{src_article}]]."
        )
        body = "\n".join(lines) + "\n"
        save_if_changed(local_page, body,
                        "Bot: create category from JA/Wikidata")
        print(f"      · created Category:{cat_name} ({tag})")

    # If we *created* an EN category, also create a JA-title redirect
    if (not existed) and via_en:
        ja_redirect = shinto.pages[f"Category:{ja_cat}"]
        if not ja_redirect.exists:
            red_body = (
                f"#redirect [[Category:{cat_name}]]\n"
                f"[[Category:{TAG_REDIRECT}]]\n"
                f"[[Category:{TIER2_CAT}]]\n"
            )
            save_if_changed(ja_redirect, red_body,
                            "Bot: jawiki-title redirect to EN category")
            print(f"        · created redirect Category:{ja_cat}")

    return local_page.name

def add_category_to_article(article: str, cat_full: str):
    pg   = shinto.pages[article]
    txt  = pg.text()
    if f"[[{cat_full}]]" in txt:
        return
    new = txt.rstrip() + f"\n[[{cat_full}]]\n"
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
            qid     = ja_cat_qid(ja_cat)
            en_name = wd_sitelinks(qid).get("en") if qid else None
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
