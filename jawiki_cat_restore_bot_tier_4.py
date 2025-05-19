#!/usr/bin/env python3
"""
jawiki_cat_restore_bot_tier_4.py  –  JA-wiki → local category sync (tier‑4 v‑2025‑05‑19‑fix)
================================================================================================
Bug‑fix: do **not** shadow the `ja` Site object — use `ja_title` for the
Japanese page title. Previous version crashed with
`'str' object has no attribute 'api'`.

Other behaviour (Tier‑4 tags, enwiki tagging, redirect handling) unchanged.
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

TIER_MAIN = "Tier 4 Categories"
TIER_WITH = "Tier 4 Categories with enwiki"
TIER_NOEN = "Tier 4 Categories with no enwiki"

# ─── MW SESSIONS ────────────────────────────────────────────────────
shinto = mwclient.Site(SHINTO_URL, path=SHINTO_PATH); shinto.login(USERNAME,PASSWORD)
ja_site = mwclient.Site(JA_URL, path=JA_PATH)           # read-only
print("Logged in")

# ─── UTILITIES ─────────────────────────────────────────────────────
ILL_JA_RE = re.compile(r"\[\[\s*ja:([^|\]]+)", re.I)
EN_IW_RE  = re.compile(r"\[\[\s*en:Category:[^\]]+\]\]", re.I)


def ensure_line(body: str, line: str) -> str:
    if line not in body:
        if not body.endswith("\n"):
            body += "\n"
        body += line + "\n"
    return body

def strip_line(body: str, line: str) -> str:
    return body.replace(line + "\n", "").replace(line, "")

# ─── WIKIDATA HELPERS ──────────────────────────────────────────────

def ja_cat_qid(cat: str) -> Optional[str]:
    d = ja_site.api(action='query', prop='pageprops', titles=f"Category:{cat}",
                    ppprop='wikibase_item', format='json')
    return next(iter(d['query']['pages'].values())).get('pageprops', {}).get('wikibase_item')


def wd_sitelinks(qid: str) -> Dict[str, str]:
    if not qid:
        return {}
    j = requests.get(WD_API, params={"action":"wbgetentities","ids":qid,"props":"sitelinks","format":"json"}, timeout=20).json()
    sl = j.get('entities', {}).get(qid, {}).get('sitelinks', {})
    return {k[:-4]: v['title'].split(':', 1)[-1] for k, v in sl.items() if k.endswith('wiki')}

# ─── CORE (unchanged except bug‑fix) ───────────────────────────────
REDIR_RX = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)\]\]", re.I)

# … (functions build_or_update_category, tag_article remain identical) …
#   ↳ omitted here for brevity; only the main‑loop variable names changed

# ─── MAIN LOOP ─────────────────────────────────────────────────────

def first_ja_link(text: str) -> Optional[str]:
    m = ILL_JA_RE.search(text)
    return urllib.parse.unquote(m.group(1)).replace('_', ' ') if m else None


def load_titles():
    with open(PAGES_FILE, encoding='utf-8') as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def main():
    articles = load_titles()
    for idx, art in enumerate(articles, 1):
        print(f"\n{idx}/{len(articles)} → [[{art}]]")
        art_pg = shinto.pages[art]
        if not art_pg.exists:
            print("  ! article missing – skipped")
            continue

        ja_title = first_ja_link(art_pg.text())
        if not ja_title:
            print("  ! no ja interwiki – skipped")
            continue
        print(f"    · jawiki: {ja_title}")

        try:
            data = ja_site.api(action='query', prop='categories', titles=ja_title,
                                clshow='!hidden', cllimit='max', format='json')
        except Exception as e:
            print("  ! failed to fetch JA cats:", e)
            continue

        page = next(iter(data['query']['pages'].values()))
        ja_cats = [c['title'].split(':', 1)[1] for c in page.get('categories', [])]
        print(f"    · {len(ja_cats)} categories")

        for ja_cat in ja_cats:
            qid = ja_cat_qid(ja_cat)
            en_name = wd_sitelinks(qid).get('en') if qid else None
            local_cat = build_or_update_category(ja_cat, en_name, art)
            tag_article(art, local_cat)
            time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    main()
