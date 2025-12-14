#!/usr/bin/env python3
"""
jawiki_cat_restore_bot_tier_4.py  –  JA‑wiki → local category sync (Tier‑2, 2025‑05‑19)
================================================================================
* Fixes variable shadowing bug **and** restores the missing helper functions
  (`build_or_update_category`, `tag_article`) so the script runs end‑to‑end.
* Adds/updates en‑wiki interwiki, Tier‑2 tags, and mutually exclusive
  *with/without enwiki* tags exactly as requested.
"""
import os, sys, time, urllib.parse, re, requests, mwclient
from typing import Dict, List, Optional
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SHINTO_URL = "shinto.miraheze.org"; SHINTO_PATH = "/w/"
JA_URL     = "ja.wikipedia.org";     JA_PATH    = "/w/"
USERNAME   = "Immanuelle";           PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"; THROTTLE = 0.1
WD_API     = "https://www.wikidata.org/w/api.php"

TAG_EXISTING = "Existing categories confirmed with Wikidata"
TAG_EN_NEW   = "Categories created from enwiki title"
TAG_JA_NEW   = "Categories created from jawiki title"
TAG_REDIRECT = "jawiki redirect categories"

TIER_MAIN = "De Tier 2 Categories"
TIER_WITH = "De Tier 2 Categories with enwiki"
TIER_NOEN = "De Tier 2 Categories with no enwiki"

# ─── MW SESSIONS ────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH); shinto.login(USERNAME, PASSWORD)
ja_site = mwclient.Site(JA_URL, path=JA_PATH)
print("Logged in")

# ─── REGEXES ───────────────────────────────────────────────────────
ILL_JA_RE = re.compile(r"\[\[\s*ja:([^|\]]+)", re.I)
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

def ja_cat_qid(cat: str) -> Optional[str]:
    d = ja_site.api(action='query', prop='pageprops', titles=f"Category:{cat}", ppprop='wikibase_item', format='json')
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

def build_or_update_category(ja_cat: str, en_title: Optional[str], src: str) -> str:
    # redirect case
    red_tgt = existing_redirect_target(ja_cat)
    if red_tgt:
        tgt_pg = shinto.pages[red_tgt]
        body = ensure_line(tgt_pg.text(), f"[[Category:{TIER_MAIN}]]")
        save_if_changed(tgt_pg, body, "Bot: ensure Tier‑2 tag")
        return red_tgt

    name = en_title or ja_cat
    page = shinto.pages[f"Category:{name}"]
    existed = page.exists
    tag = TAG_EXISTING if existed else (TAG_EN_NEW if en_title else TAG_JA_NEW)

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

    body = ensure_line(body, f"[[ja:Category:{ja_cat}]]")

    qid = ja_cat_qid(ja_cat)
    for code, title in wd_sitelinks(qid).items():
        if code in ("ja", "en"):
            continue
        body = ensure_line(body, f"[[{code}:Category:{title}]]")

    if not existed:
        body += f"\nThis category was created from JA→Wikidata links on [[{src}]].\n"
    save_if_changed(page, body, "Bot: update/create Tier‑2 category")

    # create JA redirect if we just created an EN cat
    if en_title and not existed:
        ja_red = shinto.pages[f"Category:{ja_cat}"]
        if not ja_red.exists:
            red_body = f"#redirect [[Category:{name}]]\n[[Category:{TAG_REDIRECT}]]\n[[Category:{TIER_MAIN}]]\n"
            save_if_changed(ja_red, red_body, "Bot: JA title redirect to EN cat")
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

def first_ja_link(text: str) -> Optional[str]:
    m = ILL_JA_RE.search(text)
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
        ja_title = first_ja_link(art_pg.text())
        if not ja_title:
            print("  ! no ja interwiki – skip"); continue
        try:
            data = ja_site.api(action='query', prop='categories', titles=ja_title,
                               clshow='!hidden', cllimit='max', format='json')
        except Exception as e:
            print("  ! JA fetch failed", e); continue
        page = next(iter(data['query']['pages'].values()))
        ja_cats = [c['title'].split(':', 1)[1] for c in page.get('categories', [])]
        for jc in ja_cats:
            en = wd_sitelinks(ja_cat_qid(jc)).get('en') if ja_cat_qid(jc) else None
            local = build_or_update_category(jc, en, art)
            tag_article(art, local)
            time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    main()
