#!/usr/bin/env python3
"""
fix_shikinaisha_lists.py  ─  FINAL (mwclient-only)

• Uses mwclient to read pages from  https://shinto.miraheze.org
• Uses raw HTTPS (requests) for every Wikidata call
• No Pywikibot, no family files, no SingleSiteFamily

Run with --dry-run first.
"""

from __future__ import annotations
import argparse, json, logging, re, sys, time
from typing import Any, Dict, List

import requests, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── Shinto-wiki credentials (read-only is fine) ──────────────────────────
SW_API  = "https://shinto.miraheze.org/w/api.php"
SW_USER = ""              # leave empty for anonymous read
SW_PASS = ""

# ─── Wikidata BotPassword credentials ────────────────────────────────────
WD_USER = "EmmaBot@EmmaBotGeniTestBot"   # ← change
WD_PASS = "botpassword"                        # ← change

# ─── constants ────────────────────────────────────────────────────────────
EDIT_DELAY  = 2
MAX_RETRIES = 8

LIST_CAT   = "Category:Lists of Shikinaisha by location"
SKIP_PAGES = {
    "List of Shikinaisha in Awa Province",
    "List of Shikinaisha in the Imperial Palace",
}

Q_WMLIST, Q_LIST, Q_CHAPTER, Q_ENGI = "Q13406463", "Q12139612", "Q1980247", "Q11064932"
P31, P361, P301, P910 = "P31", "P361", "P301", "P910"

WD_API = "https://www.wikidata.org/w/api.php"
SESSION, TOKEN = requests.Session(), ""


###########################################################################
# Wikidata helpers (requests + retries)
###########################################################################
def wd_api(params: Dict[str, Any], *, post=False) -> Dict[str, Any]:
    for _ in range(MAX_RETRIES):
        r = SESSION.post(WD_API, data=params, timeout=60) if post else SESSION.get(WD_API, params=params, timeout=60)
        try:
            data = r.json()
        except ValueError:
            time.sleep(EDIT_DELAY); continue
        if r.status_code in (429, 503) or "error" in data:
            time.sleep(5); continue
        return data
    raise RuntimeError("Wikidata API failed")

def login_wd():
    lg = wd_api({"action":"query","meta":"tokens","type":"login","format":"json"})["query"]["tokens"]["logintoken"]
    wd_api({"action":"login","lgname":WD_USER,"lgpassword":WD_PASS,"lgtoken":lg,"format":"json"}, post=True)
    global TOKEN
    TOKEN = wd_api({"action":"query","meta":"tokens","format":"json"})["query"]["tokens"]["csrftoken"]

def wd_write(payload: Dict[str, Any], summary: str, dry: bool) -> Dict[str, Any]:
    if dry:
        logging.debug("DRY – %s", summary); return {"entity":{"id":"DRY"}}
    payload.update({"action":"wbeditentity","format":"json","token":TOKEN,
                    "summary":summary,"bot":1,"maxlag":"5"})
    for _ in range(MAX_RETRIES):
        r = SESSION.post(WD_API, data=payload, timeout=60)
        if r.status_code in (429, 503):
            time.sleep(5); continue
        try:
            data = r.json(); time.sleep(EDIT_DELAY); return data
        except ValueError:
            time.sleep(5)
    raise RuntimeError("Wikidata write failed")

def wd_ent(qid:str)->Dict[str,Any]:
    return wd_api({"action":"wbgetentities","ids":qid,"format":"json"})["entities"][qid]

def stmt(pid:str,qid:str)->Dict[str,Any]:
    return {"mainsnak":{"snaktype":"value","property":pid,
            "datavalue":{"value":{"entity-type":"item","numeric-id":int(qid[1:])},
                         "type":"wikibase-entityid"}},
            "type":"statement","rank":"normal"}

def has_claim(ent,pid,qid)->bool:
    return any(c["mainsnak"]["datavalue"]["value"]["numeric-id"]==int(qid[1:])
               for c in ent.get("claims",{}).get(pid,[]))

###########################################################################
# mwclient helpers for ShintoWiki
###########################################################################
def sw_site():
    host = "shinto.miraheze.org"
    site = mwclient.Site(host, path="/w/")
    if SW_USER and SW_PASS:
        site.login(SW_USER, SW_PASS)
    return site

def list_pages(site) -> List[mwclient.page.Page]:
    cat = site.categories[LIST_CAT]
    return list(cat.members(namespaces=[0]))   # only content pages

###########################################################################
# per-page processing
###########################################################################
def process(page: mwclient.page.Page, dry: bool):
    title = page.name
    logging.info(" • %s", title)

    try:
        text = page.text()
    except (APIError, InvalidPageTitle):
        logging.warning("   ✗ cannot read page"); return

    m = re.search(r"\[\[d:(Q\d+)\]\]", text)
    if not m:
        logging.warning("   ✗ no [[d:Q…]] link"); return
    q_list = m.group(1)
    ent = wd_ent(q_list)

    # --- remove obsolete P31 --------------------------------------------
    rem = [c for c in ent.get("claims",{}).get(P31,[])
           if c["mainsnak"]["datavalue"]["value"]["numeric-id"]==int(Q_WMLIST[1:])]
    if rem:
        ids = "|".join(c["id"] for c in rem)
        wd_write({"action":"wbremoveclaims","claim":ids},
                 "Remove P31 = Wikimedia list article", dry)

    # --- add P31 list & chapter -----------------------------------------
    adds = [stmt(P31, q) for q in (Q_LIST, Q_CHAPTER) if not has_claim(ent,P31,q)]
    if adds:
        wd_write({"id":q_list,"data":json.dumps({"claims":adds})},
                 "Add P31 list/chapter", dry)

    # --- add P361 Engishiki ---------------------------------------------
    if not has_claim(ent,P361,Q_ENGI):
        wd_write({"id":q_list,"data":json.dumps({"claims":[stmt(P361,Q_ENGI)]})},
                 "Add P361 Engishiki Jinmyocho", dry)

    # --- labels & wipe descriptions -------------------------------------
    wd_write({"id":q_list,"data":json.dumps({
        "labels":{"en":{"language":"en","value":title},
                  "mul":{"language":"mul","value":title}},
        "descriptions":{}
    })},"Set labels; clear descriptions",dry)

    # --- handle category -------------------------------------------------
    en_cat = "Category:" + title.removeprefix("List of ")
    iw = re.search(r"\[\[ja:(.*?)\]\]", text)
    cat_qid = None
    if iw:
        ja_title = iw.group(1)
        ja = wd_api({"action":"query","titles":ja_title,"prop":"pageprops",
                     "ppprop":"wikibase_item","format":"json"})
        ja_page = next(iter(ja["query"]["pages"].values()))
        cat_qid = ja_page.get("pageprops", {}).get("wikibase_item")

    if not cat_qid:
        logging.info("   – no ja-category item; skipping P301/P910"); return

    cat_ent = wd_ent(cat_qid)
    if not has_claim(cat_ent,P301,q_list):
        wd_write({"id":cat_qid,"data":json.dumps({"claims":[stmt(P301,q_list)]})},
                 "Set P301 main topic", dry)
    if not has_claim(ent,P910,cat_qid):
        wd_write({"id":q_list,"data":json.dumps({"claims":[stmt(P910,cat_qid)]})},
                 "Set P910 category", dry)
    wd_write({"id":cat_qid,"data":json.dumps({"labels":{
        "en":{"language":"en","value":en_cat},
        "mul":{"language":"mul","value":en_cat}}})},
        "Set category labels", dry)

###########################################################################
# main
###########################################################################
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    login_wd()
    site = sw_site()

    for page in list_pages(site):
        if page.name in SKIP_PAGES:
            logging.info(" • %s (skipped)", page.name); continue
        process(page, args.dry_run)

    logging.info("✓ Finished.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted")
