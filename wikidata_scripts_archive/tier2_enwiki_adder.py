#!/usr/bin/env python3
"""
tier2_enwiki_adder.py
=====================

Walks every category in **[[Category:Tier 2 Categories with no enwiki]]**
and tries to add an English-Wikipedia interwiki link via the jawiki sitelink.

Steps for each category C:
1. Inspect page text – find the first jawiki sitelink  `[[ja:Category:Foo]]`.
2. Query that jawiki category’s Wikidata item; if an **enwiki** sitelink
   exists → add `[[en:Category:Bar]]` to C, unless already present.
3. Change maintenance categories:
     • remove `[[Category:Tier 2 Categories with no enwiki]]`
     • append `[[Category:Tier 2 Categories with enwiki]]`
   (only if the enwiki link was successfully added).

Nothing else is modified. If no jawiki link or no enwiki sitelink is found,
page is left untouched.
"""
import re, time, urllib.parse, mwclient, requests
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "EmmaBot"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE  = 0.4
SOURCE_CAT = "Tier 2 Categories with no enwiki"
DST_CAT    = "Tier 2 Categories with enwiki"

WD_API = "https://www.wikidata.org/w/api.php"
UA     = {"User-Agent": "tier2-enwiki-adder/1.0 (User:EmmaBot)"}
JA_RE  = re.compile(r"\[\[\s*ja:Category:([^\]|]+)", re.I)
EN_RE  = re.compile(r"\[\[\s*en:Category:[^\]]+\]\]", re.I)

# ─── HELPERS ─────────────────────────────────────────────────────────

def wikidata_qid(jacat: str) -> str | None:
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

    # fetch members of source category
    cm = site.api(action='query', list='categorymembers',
                  cmtitle=f"Category:{SOURCE_CAT}", cmtype='subcat|page',
                  cmlimit='max', format='json')['query']['categorymembers']

    for m in cm:
        title = m['title']           # e.g. Category:Foo
        pg    = site.pages[title]
        txt   = pg.text()
        print("→", title)

        if EN_RE.search(txt):
            print("   • already has enwiki; skipping")
            continue

        jm = JA_RE.search(txt)
        if not jm:
            print("   • no jawiki link; skipping")
            continue
        ja_cat = urllib.parse.unquote(jm.group(1)).replace('_',' ')
        print("   • jawiki:", ja_cat)

        qid = wikidata_qid(ja_cat)
        if not qid:
            print("   • no qid; skipping")
            continue
        en_name = en_sitelink(qid)
        if not en_name:
            print("   • no enwiki sitelink; skipping")
            continue
        print("   • enwiki:", en_name)

        # build new wikitext
        new_txt = txt.rstrip() + f"\n[[en:Category:{en_name}]]\n"
        new_txt = new_txt.replace(f"[[Category:{SOURCE_CAT}]]", "").rstrip()
        new_txt += f"\n[[Category:{DST_CAT}]]\n"

        try:
            pg.save(new_txt, summary="Bot: add enwiki interwiki via jawiki/Wikidata")
            print("   ✓ enwiki link added + recat")
        except APIError as e:
            print("   ! save failed:", e.code)
        time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()