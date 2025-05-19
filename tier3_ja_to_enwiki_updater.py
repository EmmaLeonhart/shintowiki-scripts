#!/usr/bin/env python3
"""
tier3_ja_to_enwiki_updater.py
=============================

Walk every subcategory of **Category:Tier 3 Categories**.  If the page has a
jawiki inter‑wiki
    [[ja:Category:Foo]]
then via that jawiki title → Wikidata → check whether an **enwiki category**
sitelink exists.  If yes:
    * Ensure the local page is **not** in
          [[Category:Tier 2 Categories with no enwiki]]
      (remove if present)
    * Ensure it **is** in
          [[Category:Tier 2 Categories with enwiki]]

No other edits are made; pages without a ja‑link or without an enwiki
sitelink are left untouched.
"""
import re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE  = 0.4

SRC_CAT   = "Tier 3 Categories"           # where we iterate
TAG_NO    = "Tier 2 Categories with no enwiki"
TAG_YES   = "Tier 2 Categories with enwiki"

JA_LINK   = re.compile(r"\[\[\s*ja:Category:([^\]|]+)", re.I)
WD_API    = "https://www.wikidata.org/w/api.php"
UA        = {"User-Agent": "tier3-ja2enwiki/1.0 (User:Immanuelle)"}

# ─── WIKIDATA HELPERS ─────────────────────────────────────────────-

def qid_from_jacat(jacat: str) -> str | None:
    r = requests.get(WD_API, params={
        "action":"query","prop":"pageprops","titles":f"Category:{jacat}",
        "ppprop":"wikibase_item","site":"jawiki","format":"json"}, headers=UA, timeout=10)
    pg = next(iter(r.json()['query']['pages'].values()))
    return pg.get('pageprops', {}).get('wikibase_item')


def en_sitelink(qid: str) -> str | None:
    r = requests.get(WD_API, params={
        "action":"wbgetentities","ids":qid,"props":"sitelinks",
        "sitefilter":"enwiki","format":"json"}, headers=UA, timeout=10)
    ent = r.json()['entities'].get(qid, {})
    sl  = ent.get('sitelinks', {}).get('enwiki')
    if sl:
        return sl['title'].split(':',1)[-1]
    return None

# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in – scanning Tier‑3 cats for ja→enwiki…")

    cats = site.api(action='query', list='categorymembers', cmtitle=f"Category:{SRC_CAT}",
                    cmtype='subcat', cmlimit='max', format='json')['query']['categorymembers']

    for ent in cats:
        full = ent['title']
        cat_name = full.split(':',1)[1]
        page = site.pages[full]
        if page.redirect:
            continue
        text = page.text()
        jm = JA_LINK.search(text)
        if not jm:
            continue
        ja_cat = urllib.parse.unquote(jm.group(1)).replace('_',' ')
        qid = qid_from_jacat(ja_cat)
        if not qid:
            continue
        if not en_sitelink(qid):
            continue  # no enwiki sitelink

        print("→", cat_name, "• enwiki exists – retag")
        changed = False
        if f"[[Category:{TAG_NO}]]" in text:
            text = text.replace(f"[[Category:{TAG_NO}]]", "")
            changed = True
        if f"[[Category:{TAG_YES}]]" not in text:
            text = text.rstrip()+f"\n[[Category:{TAG_YES}]]\n"
            changed = True
        if changed:
            try:
                page.save(text, summary="Bot: mark Tier‑3 cat as having enwiki")
                print("   • tags updated")
            except APIError as e:
                print("   ! save failed", e.code)
        time.sleep(THROTTLE)

    print("Done.")

if __name__ == "__main__":
    main()
