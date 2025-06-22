#!/usr/bin/env python3
"""sync_person_infobox.py – v1.1
--------------------------------
Extends the previous bot to add new mappings:
* **P361** → `organization`        (part of / affiliated org)
* **P1559** → `native_name`        (name in native language)
* **P735** → `given_name`
* **P119** → `resting_place`       (place of burial)

Run:
    python sync_person_infobox.py

Dependencies: mwclient, mwparserfromhell, pymongo, requests.
"""
# ── CONFIG ────────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"

TARGET_QID = "Q5"

PROPS = [
    "P18","P569","P570","P19","P20","P21","P27","P106","P39","P26","P40",
    "P22","P25","P3373","P53","P166","P800","P140","P149",
    "P361","P1559","P735","P119"
]

WD2INFOBOX = {
    "P18"  : "image",
    "P569" : "birth_date",
    "P570" : "death_date",
    "P19"  : "birth_place",
    "P20"  : "death_place",
    "P21"  : "gender",
    "P27"  : "nationality",
    "P106" : "occupation",
    "P39"  : "title",
    "P26"  : "spouse",
    "P40"  : "children",
    "P22"  : "father",
    "P25"  : "mother",
    "P3373": "relatives",
    "P53"  : "family",
    "P166" : "awards",
    "P800" : "notable_works",
    "P140" : "religion",
    "P149" : "style",
    "P361" : "organization",
    "P1559": "native_name",
    "P735" : "given_name",
    "P119" : "resting_place",
}

# ──────────────────────────────────────────────────────────────────────────
import os, re, time, json, requests
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
    lbl=data["entities"].get(wid,{}).get("labels",{}).get("en",{}).get("value",wid)
    LABEL_CACHE[wid]=lbl; return lbl

def ill_link(wid:str)->str:
    return f"{{{{ill|{wd_label(wid)}|qid={wid}}}}}"

def format_date(val:dict, birth:bool)->str:
    """Convert a Wikidata time snak to wikitext.

    * If precision ≥11 (day) → {{birth date|YYYY|MM|DD}} / {{death date|…}}
    * If precision ==10 (month) → "YYYY-MM"
    * Otherwise → "YYYY" (signed years handled)
    Handles negative / BCE years and Wikidata "00" month or day paddings.
    """
    iso = val["time"].lstrip("+")           # e.g. "1327-00-00T…" or "-0130-05-00T…"
    date_part = iso.split("T")[0]            # drop time zone
    segments = [seg for seg in date_part.split("-") if seg != ""]  # remove empty from BCE
    year = segments[0] if segments else ""
    month = segments[1] if len(segments) > 1 else "00"
    day = segments[2] if len(segments) > 2 else "00"
    prec = val.get("precision", 9)

    if prec >= 11 and month != "00" and day != "00":
        return f"{{{{{'birth' if birth else 'death'} date|{year}|{int(month)}|{int(day)}}}}}"
    if prec == 10 and month != "00":
        return f"{year}-{month}"
    return year

# ---------- fetch selected props ----------------------------------------

def wd_get(qid:str)->Dict[str,List[str]]:
    ent=requests.get(WD_API,params={"action":"wbgetentities","ids":qid,
        "props":"claims","languages":"en|ja","format":"json"},timeout=20).json()
    ent=ent["entities"].get(qid,{})
    out={p:[] for p in PROPS}
    for pid in PROPS:
        for st in ent.get("claims",{}).get(pid,[]):
            dv=st["mainsnak"].get("datavalue",{})
            if not dv: continue
            typ=dv["type"]; val=dv["value"]
            if pid in ("P569","P570") and typ=="time":
                out[pid].append(format_date(val,pid=="P569"))
            elif typ=="wikibase-entityid":
                out[pid].append(ill_link(val["id"]))
            elif typ=="monolingualtext":
                out[pid].append(val.get("text"))
            elif typ=="string":
                out[pid].append(val)
    return out

# ---------- Infobox patcher ---------------------------------------------
INFO_RX=re.compile(r"Infobox\s+person",re.I)

def patch(text:str,data:Dict[str,List[str]]):
    code=mwp.parse(text)
    tpl=next((t for t in code.filter_templates() if INFO_RX.match(str(t.name))),None)
    if not tpl:
        tpl=mwp.nodes.Template("Infobox person"); code.insert(0,tpl)
    for pid,vals in data.items():
        if not vals: continue
        param=WD2INFOBOX[pid]
        uniq="; ".join(sorted(set(vals)))
        tpl.add(param, f"File:{vals[0].split(':')[-1]}" if pid=="P18" else uniq)
    return str(code)

# ---------- Mongo helpers -----------------------------------------------
CLAIM="claims.P31.mainsnak.datavalue.value.id"

def people(col):
    for d in col.find({CLAIM:TARGET_QID}):
        title=(d.get("shinto_titles") or d.get("page_title") or d.get("title"))
        if not title: continue
        qid=d.get("id") or d.get("qid") or d.get("QID")
        yield title,qid

# ---------- main ---------------------------------------------------------

def main():
    col=MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages=list(people(col))
    print(f"{len(pages)} people found")
    site=mwclient.Site(WIKI_URL,path=WIKI_PATH); site.login(USERNAME,PASSWORD)

    for title,qid in pages:
        page=site.pages[title]
        if not page.exists: print(f"✗ {title} missing"); continue
        data=wd_get(qid)
        new=patch(page.text(),data)
        if new==page.text():
            print(f"• {title} ok"); continue
        try:
            page.save(new,summary="Bot: sync Person infobox from Wikidata (extended)",minor=True)
            print(f"✔ {title}"); time.sleep(THROTTLE)
        except APIError as e:
            print(f"! {title}: {e.code}")

if __name__=="__main__":
    main()
