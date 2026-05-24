#!/usr/bin/env python3
"""
Category Interwiki Restore Bot – Tier‑2 Category Generator (v2)
==============================================================
Fix: accept raw titles *with or without* the “Category:” prefix in
`pages.txt`. Now the script always targets the corresponding local
category page.
"""

import os, sys, re, time, urllib.parse
from typing import List, Dict, Set
import requests, mwclient
from mwclient.errors import APIError

# ── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "EmmaBot"; PASSWORD = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"; THROTTLE = 0.5
WD_API     = "https://www.wikidata.org/w/api.php"
UA         = {"User-Agent": "tier2-category-bot/2.1 (User:EmmaBot)"}
REMOTE_SITES = {
    "commons": ("commons.wikimedia.org", "/w/"),
    "ja":      ("ja.wikipedia.org", "/w/"),
    "de":      ("de.wikipedia.org", "/w/"),
}
TAG_TIER1 = "Tier 1 Categories"; TAG_TIER2 = "Tier 2 Categories"
TAG_CONFIRMED  = "Categories confirmed during Tier 2 run"
TAG_REDIRECT   = "Tier 2 redirect categories"
TAG_CREATED_FROM = {
    "en": "Categories created from enwiki title",
    "commons": "Categories created from commonswiki title",
    "ja": "Categories created from jawiki title",
    "de": "Categories created from dewiki title",
}
PRIORITY = ["en", "commons", "ja", "de"]
COMMONS_RE = re.compile(r"\{\{\s*Commons[ _]category\s*\|\s*([^}|]+)", re.I)

# ── UTILS ─────────────────────────────────────────────────────────

def load_titles() -> List[str]:
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    with open(PAGES_FILE, encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip() and not l.startswith("#")]

def ensure_cat_title(raw: str) -> str:
    return raw[9:] if raw.lower().startswith("category:") else raw

def wd_sitelinks(q: str) -> Dict[str,str]:
    r = requests.get(WD_API, params={"action":"wbgetentities","ids":q,
        "props":"sitelinks","format":"json"}, headers=UA, timeout=15)
    ent=r.json().get("entities",{}).get(q,{}).get("sitelinks",{})
    res={}
    for k,v in ent.items():
        lang=k[:-4] if k.endswith("wiki") else k
        if lang in ("en","ja","de","commons"): res[lang]=v["title"].split(":",1)[-1]
    return res

def page_qid(site, cat:str):
    d=site.api(action="query",titles=f"Category:{cat}",prop="pageprops",ppprop="wikibase_item",format="json")
    return next(iter(d["query"]["pages"].values())).get("pageprops",{}).get("wikibase_item")

def parent_cats(site, cat:str, commons=False):
    d=site.api(action="query",prop="categories",clshow="!hidden",titles=f"Category:{cat}",cllimit="max",format="json")
    p=next(iter(d["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in p.get("categories",[])]

def redirect_target(local, name:str):
    pg=local.pages[f"Category:{name}"]
    if not pg.exists: return None
    m=re.match(r"#redirect\s*\[\[Category:([^\]]+)\]\]",pg.text(),re.I)
    return m.group(1) if m else None

def append(page, text:str, lines:List[str]):
    if not lines: return
    new=text.rstrip()+"\n"+"\n".join(lines)+"\n"
    try: page.save(new,summary="Bot: sync Tier‑2 category")
    except APIError as e: print("    ! save failed",e.code)

# ── MAIN ──────────────────────────────────────────────────────────
local=mwclient.Site(LOCAL_URL,path=LOCAL_PATH); local.login(USERNAME,PASSWORD)
remote={c:mwclient.Site(u,p) for c,(u,p) in REMOTE_SITES.items()}

for idx,raw in enumerate(load_titles(),1):
    tier1=ensure_cat_title(raw)
    print(f"\n{idx}: {tier1}")
    src=local.pages[f"Category:{tier1}"]
    if not src.exists:
        print("  • source missing"); continue
    txt=src.text()
    commons_links=re.findall(COMMONS_RE,txt)+re.findall(r"\[\[commons:Category:([^]|]+)",txt,re.I)
    ja_links=re.findall(r"\[\[ja:Category:([^]|]+)",txt,re.I)
    de_links=re.findall(r"\[\[de:Category:([^]|]+)",txt,re.I)

    qids:Dict[str,Dict[str,str]]={}
    seen:Set[str]=set()
    def harvest(cat,code):
        q=page_qid(remote[code],cat)
        if not q or q in seen: return
        seen.add(q); qids[q]=wd_sitelinks(q)
        for p in parent_cats(remote[code],cat,commons=(code=='commons')):
            pq=page_qid(remote[code],p)
            if pq and pq not in seen:
                seen.add(pq); qids[pq]=wd_sitelinks(pq)
    for c in commons_links: harvest(c,'commons')
    for j in ja_links: harvest(j,'ja')
    for d in de_links: harvest(d,'de')

    for qid,sitelinks in qids.items():
        prim_lang=next((l for l in PRIORITY if l in sitelinks),None)
        if not prim_lang: continue
        prim=urllib.parse.unquote(sitelinks[prim_lang]).replace('_',' ')
        prim=redirect_target(local,prim) or prim
        cat_pg=local.pages[f"Category:{prim}"]
        exists=cat_pg.exists and not cat_pg.redirect
        base=cat_pg.text() if exists else ""
        add=[]
        # tag
        tag= f"[[Category:{TAG_CONFIRMED}]]" if exists else f"[[Category:{TAG_CREATED_FROM[prim_lang]}]]"
        if tag not in base: add.append(tag)
        # qid template
        if qid not in base: add.append(f"{{{{Wikidata|{qid}}}}}")
        # interwikis
        def iw(l,t):
            if l=='en': return f"<!--enwiki-->\n[[en:Category:{t}]]"
            if l=='commons': return f"<!--commons-->\n{{{{Commons category|{t}}}}}"
            if l=='ja': return f"<!--jawiki-->\n[[ja:Category:{t}]]"
            return f"<!--dewiki-->\n[[de:Category:{t}]]"
        for l,t in sitelinks.items():
            line=iw(l,urllib.parse.unquote(t).replace('_',' '))
            if line not in base: add.append(line)
        # tier2 tag
        if TAG_TIER1 not in base and f"[[Category:{TAG_TIER2}]]" not in base:
            add.append(f"[[Category:{TAG_TIER2}]]")
        append(cat_pg,base,add)
        # redirects other names
        for l,t in sitelinks.items():
            t=urllib.parse.unquote(t).replace('_',' ')
            if t==prim: continue
            r=local.pages[f"Category:{t}"]
            if not r.exists:
                append(r,"",[f"#REDIRECT [[Category:{prim}]]\n[[Category:{TAG_REDIRECT}]]"])
    time.sleep(THROTTLE)
print("Done")
