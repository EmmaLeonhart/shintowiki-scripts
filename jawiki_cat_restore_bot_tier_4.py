#!/usr/bin/env python3
"""
jawiki_cat_restore_bot_tier_4.py  –  JA‑wiki → local category sync (tier‑4 v‑2025‑05‑19)
==============================================================================

Key differences from your previous version
------------------------------------------
* **Tier constants** updated – every category edited/created now carries
  `[[Category:Tier 4 Categories]]`.
* When an **English category name exists** (`en_title`):
    • adds `[[en:Category:…]]` interwiki line.
    • ensures tag `[[Category:Tier 4 Categories with enwiki]]`.
* When **no enwiki name**:
    • ensures tag `[[Category:Tier 4 Categories with no enwiki]]`.
* Opposite tag (with/without enwiki) is removed if present.
* Existing category pages are preserved; new lines are *appended* if missing.

Everything else (redirect handling, JA → redirect, Tier‑4 tag propagation,
adding category to articles) stays the same.
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
ja     = mwclient.Site(JA_URL, path=JA_PATH)  # read‑only
print("Logged in")

# ─── SIMPLE UTILITIES ──────────────────────────────────────────────
ILL_JA_RE = re.compile(r"\[\[\s*ja:([^|\]]+)", re.I)
EN_IW_RE  = re.compile(r"\[\[\s*en:Category:[^\]]+\]\]", re.I)

def ensure_line(body:str,line:str):
    if line not in body:
        if not body.endswith("\n"):
            body+="\n"
        body+=line+"\n"
    return body

def strip_line(body:str,line:str):
    return body.replace(line+"\n","").replace(line,"")

# ─── WIKIDATA HELPERS ──────────────────────────────────────────────

def ja_cat_qid(cat:str)->Optional[str]:
    d=ja.api(action='query',prop='pageprops',titles=f"Category:{cat}",ppprop='wikibase_item',format='json')
    return next(iter(d['query']['pages'].values())).get('pageprops',{}).get('wikibase_item')

def wd_sitelinks(qid:str)->Dict[str,str]:
    if not qid:
        return {}
    j=requests.get(WD_API,params={"action":"wbgetentities","ids":qid,"props":"sitelinks","format":"json"},timeout=20).json()
    sl=j.get('entities',{}).get(qid,{}).get('sitelinks',{})
    return {k[:-4]:v['title'].split(':',1)[-1] for k,v in sl.items() if k.endswith('wiki')}

# ─── CORE FUNCTIONS ────────────────────────────────────────────────
REDIR_RX=re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)\]\]",re.I)

def existing_redirect_target(cat:str)->Optional[str]:
    pg=shinto.pages[f"Category:{cat}"]
    if not pg.exists: return None
    m=REDIR_RX.match(pg.text().strip())
    return f"Category:{m.group(1).strip()}" if m else None

# preserve‑append helper

def save_if_changed(page,new,summary):
    if new!=page.text():
        try:
            page.save(new,summary=summary)
        except APIError as e:
            print("    ! save failed",e.code)

def build_or_update_category(ja_cat:str,en_title:Optional[str],source:str)->str:
    red_target=existing_redirect_target(ja_cat)
    if red_target:
        tgt=shinto.pages[red_target]
        body=tgt.text()
        body=ensure_line(body,f"[[Category:{TIER_MAIN}]]")
        save_if_changed(tgt,body,"Bot: ensure Tier‑4 tag")
        return red_target

    name=en_title or ja_cat
    page=shinto.pages[f"Category:{name}"]
    existed=page.exists
    tag = TAG_EXISTING if existed else (TAG_EN_NEW if en_title else TAG_JA_NEW)

    if existed:
        body=page.text()
    else:
        body=""
    # mandatory tags
    body=ensure_line(body,f"[[Category:{tag}]]")
    body=ensure_line(body,f"[[Category:{TIER_MAIN}]]")

    # enwiki interwiki presence
    if en_title:
        body=ensure_line(body,f"[[en:Category:{en_title}]]")
        body=strip_line(body,f"[[Category:{TIER_NOEN}]]")
        body=ensure_line(body,f"[[Category:{TIER_WITH}]]")
    else:
        body=strip_line(body,f"[[Category:{TIER_WITH}]]")
        body=ensure_line(body,f"[[Category:{TIER_NOEN}]]")

    # ja link always
    body=ensure_line(body,f"[[ja:Category:{ja_cat}]]")

    # other interwikis
    qid=ja_cat_qid(ja_cat)
    for code,title in wd_sitelinks(qid).items():
        if code in ("ja","en"): continue
        body=ensure_line(body,f"[[{code}:Category:{title}]]")

    # provenance line for new cats
    if not existed:
        body+=f"\nThis category was created from JA→Wikidata links on [[{source}]].\n"
    save_if_changed(page,body,"Bot: update/create Tier‑4 category")

    # create redirect from JA title to EN‑title if we just created an EN cat
    if en_title and not existed:
        ja_red=shinto.pages[f"Category:{ja_cat}"]
        if not ja_red.exists:
            red_body=(f"#redirect [[Category:{name}]]\n[[Category:{TAG_REDIRECT}]]\n[[Category:{TIER_MAIN}]]\n")
            save_if_changed(ja_red,red_body,"Bot: redirect JA title → EN cat")
    return page.name

# ─── MISC UTILS ────────────────────────────────────────────────────
ILL_JA=re.compile(r"\[\[\s*ja:([^|\]]+)",re.I)

def first_ja_link(text:str)->Optional[str]:
    m=ILL_JA.search(text); return urllib.parse.unquote(m.group(1)).replace('_',' ') if m else None

# read list
def load_titles():
    with open(PAGES_FILE,encoding='utf-8') as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]

# add cat to article

def tag_article(article,cat_full):
    pg=shinto.pages[article]
    if f"[[{cat_full}]]" in pg.text():
        return
    new=pg.text().rstrip()+f"\n[[{cat_full}]]\n"
    try:
        pg.save(new,summary=f"Bot: add category {cat_full}")
        print("      • tagged",article)
    except APIError as e:
        print("      ! tagging",article,e.code)

# ─── MAIN LOOP ─────────────────────────────────────────────────────

def main():
    articles=load_titles()
    for i,title in enumerate(articles,1):
        print(f"\n{i}/{len(articles)} → [[{title}]]")
        art=shinto.pages[title]
        if not art.exists:
            print("  ! missing – skip"); continue
        ja=first_ja_link(art.text())
        if not ja:
            print("  ! no ja link – skip"); continue
        try:
            cats=ja.api(action='query',prop='categories',titles=ja,clshow='!hidden',cllimit='max',format='json')
        except Exception as e:
            print("  ! fetch cats failed",e); continue
        page=list(cats['query']['pages'].values())[0]
        cat_list=[c['title'].split(':',1)[1] for c in page.get('categories',[])]
        print("    ·",len(cat_list),"categories")
        for jc in cat_list:
            qid=ja_cat_qid(jc)
            en=wd_sitelinks(qid).get('en') if qid else None
            local=build_or_update_category(jc,en,title)
            tag_article(title,local)
            time.sleep(THROTTLE)
    print("Done.")

if __name__=='__main__':
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    main()
