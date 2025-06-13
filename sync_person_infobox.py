#!/usr/bin/env python3
"""sync_person_infobox.py
========================
Populate‑or‑patch **{{Infobox person}}** for every page whose *instance of*
`P31` equals **human (Q5)**.  The script is intentionally *maximalist*: it
pulls 20 + core properties, formats them for the infobox, and leaves existing
parameters intact unless it needs to add a value.

**Wikidata → Infobox mapping**
-------------------------------------------------------------------
P18  → image
P569 → birth_date         ({{birth date|YYYY|MM|DD}} if precision ≥ day)
P570 → death_date         ({{death date|YYYY|MM|DD}} …)
P19  → birth_place        (ill link)
P20  → death_place        (ill link)
P21  → gender             (|honorific_prefix= or |gender= )  # stored in gender
P27  → nationality        (ill link / label)
P106 → occupation         (semicolon‑separated ill links)
P39  → position_held      (→ |title=  append)
P26  → spouse             (|spouse= ill links)
P40  → children           (|children= ill links)
P22  → father             (|father= ill link)
P25  → mother             (|mother= ill link)
P3373→ sibling            (|relatives= …)  (siblings grouped)
P53  → family             (|family= ill link)
P166 → awards             (|awards= …)
P800 → notable_works      (|notable_works= …)
P140 → religion           (|religion= …)
P149 → style              (|style= architectural style)

You can add or drop mappings by editing `WD2INFOBOX`.

Run once:
    pip install mwclient mwparserfromhell pymongo requests

Then:
    python sync_person_infobox.py
"""
# ──────────────────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"

TARGET_QID = "Q5"   # human

PROPS = [
    "P18","P569","P570","P19","P20","P21","P27","P106","P39","P26","P40",
    "P22","P25","P3373","P53","P166","P800","P140","P149"
]
WD2INFOBOX = {
    "P18" : "image",
    "P569": "birth_date",
    "P570": "death_date",
    "P19" : "birth_place",
    "P20" : "death_place",
    "P21" : "gender",
    "P27" : "nationality",
    "P106": "occupation",
    "P39" : "title",
    "P26" : "spouse",
    "P40" : "children",
    "P22" : "father",
    "P25" : "mother",
    "P3373":"relatives",
    "P53" : "family",
    "P166": "awards",
    "P800": "notable_works",
    "P140": "religion",
    "P149": "style",
}

# ──────────────────────────────────────────────────────────────────────────
import os, re, time, json, requests, datetime
from typing import Dict, List, Any
import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str,str] = {}

# ---------- Wikidata helpers --------------------------------------------

def wd_label(wid:str) -> str:
    if wid in LABEL_CACHE: return LABEL_CACHE[wid]
    data=requests.get(WD_API,params={"action":"wbgetentities","ids":wid,
        "props":"labels","languages":"en|ja","format":"json"},timeout=20).json()
    ent=data["entities"].get(wid, {})
    lbl=ent.get("labels",{}).get("en",{}).get("value") or wid
    LABEL_CACHE[wid]=lbl; return lbl


def ill_link(wid:str) -> str:
    lbl = wd_label(wid)
    return f"{{{{ill|{lbl}|qid={wid}}}}}"


def format_date(val:dict, birth:bool=True) -> str:
    iso = val["time"].lstrip("+")
    parts = iso.split("T")[0].split("-")  # YYYY-MM-DD
    y, m, d = parts[0], parts[1], parts[2]
    prec = val["precision"]
    if prec >= 11:   # day precision
        return f"{{{{{'birth' if birth else 'death'} date|{y}|{int(m):02d}|{int(d):02d}}}}}"
    elif prec == 10: # month precision
        return f"{y}-{m}"
    else:            # year or less
        return y


def wd_get(qid:str) -> Dict[str,List[str]]:
    ent=requests.get(WD_API,params={"action":"wbgetentities","ids":qid,
        "props":"claims","languages":"en|ja","format":"json"},timeout=20).json()
    ent = ent["entities"].get(qid, {})
    out={p:[] for p in PROPS}
    for pid in PROPS:
        for stmt in ent.get("claims",{}).get(pid,[]):
            dv=stmt["mainsnak"].get("datavalue",{})
            if not dv: continue
            typ=dv["type"]; val=dv["value"]
            if pid in ("P569","P570") and typ=="time":
                out[pid].append(format_date(val, pid=="P569"))
            elif typ=="wikibase-entityid":
                out[pid].append(ill_link(val["id"]))
            elif typ=="string":
                out[pid].append(val)
    return out

# ---------- Infobox patcher ---------------------------------------------
INFO_RX=re.compile(r"Infobox\s+person",re.I)

def patch_infobox(text:str,data:Dict[str,List[str]]):
    code=mwp.parse(text)
    tpl=next((t for t in code.filter_templates() if INFO_RX.match(str(t.name))),None)
    if not tpl:
        tpl=mwp.nodes.Template("Infobox person"); code.insert(0,tpl)
    for pid,vals in data.items():
        if not vals: continue
        param=WD2INFOBOX[pid]
        unique="; ".join(sorted(set(vals)))
        if pid=="P18":
            tpl.add(param,f"File:{vals[0].split(':')[-1]}")
        else:
            tpl.add(param,unique)
    return str(code)

# ---------- Mongo helpers -----------------------------------------------
CLAIM_PATH="claims.P31.mainsnak.datavalue.value.id"

def people(col):
    for doc in col.find({CLAIM_PATH:TARGET_QID}):
        title=(doc.get("shinto_titles") or doc.get("page_title") or doc.get("title"))
        if not title: continue
        qid=doc.get("id") or doc.get("qid") or doc.get("QID")
        yield title,qid

# ---------- Main loop ----------------------------------------------------

def main():
    col=MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages=list(people(col))
    print(f"Found {len(pages)} human pages in Mongo")
    site=mwclient.Site(WIKI_URL,path=WIKI_PATH); site.login(USERNAME,PASSWORD)
    for title,qid in pages:
        page=site.pages[title]
        if not page.exists:
            print(f"✗ {title} missing"); continue
        props=wd_get(qid)
        newtxt=patch_infobox(page.text(),props)
        if newtxt==page.text():
            print(f"• {title} up-to-date"); continue
        try:
            page.save(newtxt,
                      summary="Bot: sync Infobox person from Wikidata (core props)",
                      minor=True)
            print(f"✔ {title} updated"); time.sleep(THROTTLE)
        except APIError as e:
            print(f"! Failed {title}: {e.code}")

if __name__=="__main__":
    main()
