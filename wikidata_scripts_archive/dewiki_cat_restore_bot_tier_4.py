#!/usr/bin/env python3
"""
dewiki_cat_restore_bot_tier_4.py  –  de‑wiki → local category sync (Tier 8, 2025‑05‑19)
================================================================================
* Fixes variable shadowing bug **and** restores the missing helper functions
  (`build_or_update_category`, `tag_article`) so the script runs end‑to‑end.
* Adds/updates en‑wiki interwiki, Tier 8 tags, and mutually exclusive
  *with/without enwiki* tags exactly as requested.
"""
import os, sys, time, urllib.parse, re, requests, mwclient
from typing import Dict, List, Optional
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL = "shinto.miraheze.org"; SHINTO_PATH = "/w/"
de_URL     = "de.wikipedia.org";     de_PATH    = "/w/"
USERNAME   = "Immanuelle";           PASSWORD   = "[REDACTED_SECRET_2]"
PAGES_FILE = "pages.txt"; THROTTLE = 0.1
WD_API     = "https://www.wikidata.org/w/api.php"

TAG_EXISTING = "Existing categories confirmed with Wikidata"
TAG_EN_NEW   = "Categories created from enwiki title"
TAG_de_NEW   = "Categories created from dewiki title"
TAG_REDIRECT = "dewiki redirect categories"

TIER_MAIN = "De Tier 8 Categories"
TIER_WITH = "De Tier 8 Categories with enwiki"
TIER_NOEN = "De Tier 8 Categories with no enwiki"

# ─── MW SESSIONS ────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH); shinto.login(USERNAME, PASSWORD)
de_site = mwclient.Site(de_URL, path=de_PATH)
print("Logged in")

# ─── REGEXES ───────────────────────────────────────────────────────
ILL_de_RE = re.compile(r"\[\[\s*de:([^|\]]+)", re.I)
REDIR_RX  = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)\]\]", re.I)

# ─── SMALL HELPERS ─────────────────────────────────────────────────

def ensure_line(body: str, line: str) -> str:
    if line not in body:
        if not body.endswith("\n"):
            body += "\n"
        body += line + "\n"
    return body


def strip_line(body: str, line: str) -> str:
    return body.replace(line + "\n", "").replace(line, "")


def save_if_changed(page, new: str, summary: str):
    if new != page.text():
        try:
            page.save(new, summary=summary)
        except APIError as e:
            print("    ! save failed", e.code)

# ─── WIKIDATA ──────────────────────────────────────────────────────

def de_cat_qid(cat: str) -> Optional[str]:
    d = de_site.api(action='query', prop='pageprops', titles=f"Category:{cat}", ppprop='wikibase_item', format='json')
    return next(iter(d['query']['pages'].values())).get('pageprops', {}).get('wikibase_item')


def wd_sitelinks(qid: str) -> Dict[str, str]:
    if not qid:
        return {}
    j = requests.get(WD_API, params={"action":"wbgetentities","ids":qid,"props":"sitelinks","format":"json"}, timeout=20).json()
    sl = j.get('entities', {}).get(qid, {}).get('sitelinks', {})
    return {k[:-4]: v['title'].split(':', 1)[-1] for k, v in sl.items() if k.endswith('wiki')}

# ─── REDIRECT TARGET HELPER ───────────────────────────────────────

def existing_redirect_target(cat: str) -> Optional[str]:
    pg = shinto.pages[f"Category:{cat}"]
    if not pg.exists:
        return None
    m = REDIR_RX.match(pg.text())
    return f"Category:{m.group(1).strip()}" if m else None

# ─── CATEGORY CREATION / UPDATE ──────────────────────────────────

def build_or_update_category(de_cat: str, en_title: Optional[str], src: str) -> str:
    # redirect case
    red_tgt = existing_redirect_target(de_cat)
    if red_tgt:
        tgt_pg = shinto.pages[red_tgt]
        body = ensure_line(tgt_pg.text(), f"[[Category:{TIER_MAIN}]]")
        save_if_changed(tgt_pg, body, "Bot: ensure Tier 8 tag")
        return red_tgt

    name = en_title or de_cat
    page = shinto.pages[f"Category:{name}"]
    existed = page.exists
    tag = TAG_EXISTING if existed else (TAG_EN_NEW if en_title else TAG_de_NEW)

    body = page.text() if existed else ""
    body = ensure_line(body, f"[[Category:{tag}]]")
    body = ensure_line(body, f"[[Category:{TIER_MAIN}]]")

    if en_title:
        body = ensure_line(body, f"[[en:Category:{en_title}]]")
        body = strip_line(body, f"[[Category:{TIER_NOEN}]]")
        body = ensure_line(body, f"[[Category:{TIER_WITH}]]")
    else:
        body = strip_line(body, f"[[Category:{TIER_WITH}]]")
        body = ensure_line(body, f"[[Category:{TIER_NOEN}]]")

    body = ensure_line(body, f"[[de:Category:{de_cat}]]")

    qid = de_cat_qid(de_cat)
    for code, title in wd_sitelinks(qid).items():
        if code in ("de", "en"):
            continue
        body = ensure_line(body, f"[[{code}:Category:{title}]]")

    if not existed:
        body += f"\nThis category was created from de→Wikidata links on [[{src}]].\n"
    save_if_changed(page, body, "Bot: update/create Tier 8 category")

    # create de redirect if we just created an EN cat
    if en_title and not existed:
        de_red = shinto.pages[f"Category:{de_cat}"]
        if not de_red.exists:
            red_body = f"#redirect [[Category:{name}]]\n[[Category:{TAG_REDIRECT}]]\n[[Category:{TIER_MAIN}]]\n"
            save_if_changed(de_red, red_body, "Bot: de title redirect to EN cat")
    return page.name

# ─── TAG ARTICLE WITH CATEGORY ────────────────────────────────────

def tag_article(article: str, cat_full: str):
    pg = shinto.pages[article]
    if f"[[{cat_full}]]" in pg.text():
        return
    new = pg.text().rstrip() + f"\n[[{cat_full}]]\n"
    try:
        pg.save(new, summary=f"Bot: add category {cat_full}")
        print("      • tagged", article)
    except APIError as e:
        print("      ! tagging", article, e.code)

# ─── MAIN ─────────────────────────────────────────────────────────

def first_de_link(text: str) -> Optional[str]:
    m = ILL_de_RE.search(text)
    return urllib.parse.unquote(m.group(1)).replace('_', ' ') if m else None


def load_titles() -> List[str]:
    with open(PAGES_FILE, encoding='utf-8') as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def main():
    for idx, art in enumerate(load_titles(), 1):
        print(f"\n{idx} → [[{art}]]")
        art_pg = shinto.pages[art]
        if not art_pg.exists:
            print("  ! missing – skip"); continue
        de_title = first_de_link(art_pg.text())
        if not de_title:
            print("  ! no de interwiki – skip"); continue
        try:
            data = de_site.api(action='query', prop='categories', titles=de_title,
                               clshow='!hidden', cllimit='max', format='json')
        except Exception as e:
            print("  ! de fetch failed", e); continue
        page = next(iter(data['query']['pages'].values()))
        de_cats = [c['title'].split(':', 1)[1] for c in page.get('categories', [])]
        for jc in de_cats:
            en = wd_sitelinks(de_cat_qid(jc)).get('en') if de_cat_qid(jc) else None
            local = build_or_update_category(jc, en, art)
            tag_article(art, local)
            time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    main()
