#!/usr/bin/env python3
"""sync_buddhist_temple_infobox.py
---------------------------------
Populate / patch **{{Infobox Buddhist temple}}** on every page that is
*instance of* **Buddhist temple (Q5393308)** in your **shinto_wiki** MongoDB.

A. Reads the list of temples directly from Mongo (no more manual pages.txt).
B. Pulls the 7 target properties from Wikidata.
C. Adds or updates the infobox on shinto.miraheze.org.

Required Python packages:
    pip install mwclient mwparserfromhell pymongo requests
"""
# ── CONFIG ────────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4      # seconds between edits

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"      # adjust if different

TARGET_QID = "Q5393308"        # Buddhist temple
PROPS      = [                 # Wikidata props to sync → Infobox field
    "P18",   # image            → image
    "P140",  # religion         → religious_affiliation
    "P131",  # located in       → prefecture
    "P625",  # coordinates      → coordinates
    "P112",  # founded by       → founded_by
    "P825",  # dedicated to     → deity
    "P361",  # part of          → part_of
]
WD2INFOBOX = {
    "P18":  "image",
    "P140": "religious_affiliation",
    "P131": "prefecture",
    "P625": "coordinates",
    "P112": "founded_by",
    "P825": "deity",
    "P361": "part_of",
}
# ──────────────────────────────────────────────────────────────────────────
import os, time, re, sys, json, requests
from typing import Any, Dict, List

import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

# ── Wikidata helpers ─────────────────────────────────────────────────────
WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str,str] = {}

def wd_label(wid:str) -> str:
    if wid in LABEL_CACHE:
        return LABEL_CACHE[wid]
    data = requests.get(WD_API, params={
        "action":"wbgetentities","ids":wid,
        "props":"labels","languages":"en|ja","format":"json"}, timeout=20
    ).json()["entities"].get(wid, {})
    lbl = data.get("labels", {}).get("en", {}).get("value") or wid
    LABEL_CACHE[wid] = lbl
    return lbl

def wd_get_props(qid:str, props:List[str]) -> Dict[str,List[str]]:
    res = requests.get(WD_API, params={
        "action":"wbgetentities","ids":qid,
        "languages":"en|ja","props":"claims","format":"json"}, timeout=20
    ).json()["entities"].get(qid, {})
    out = {p: [] for p in props}
    for pid in props:
        for stmt in res.get("claims", {}).get(pid, []):
            dv = stmt["mainsnak"].get("datavalue", {})
            if not dv: continue
            typ = dv["type"]; val=dv["value"]
            if typ=="wikibase-entityid":
                wid = val["id"]
                en = wd_label(wid)
                out[pid].append(f"{{{{ill|{en}|qid={wid}}}}}")
            elif typ=="string":
                out[pid].append(val)
            elif typ=="globecoordinate":
                lat,lon = val["latitude"], val["longitude"]
                out[pid].append(
                    f"{{{{Coord|{lat}|N|{lon}|E|region:JP_type:landmark|display=inline,title}}}}")
    return out

# ── Infobox patcher ──────────────────────────────────────────────────────
INFONAME = re.compile(r"Infobox\s+Buddhist\s+temple", re.I)

def patch_infobox(wikitext:str, data:Dict[str,List[str]]) -> str:
    code = mwp.parse(wikitext)
    tpl = next((t for t in code.filter_templates() if INFONAME.match(str(t.name))), None)
    if not tpl:
        tpl = mwp.nodes.Template("Infobox Buddhist temple")
        code.insert(0, tpl)
    for pid, vals in data.items():
        if not vals: continue
        key = WD2INFOBOX[pid]
        if pid=="P18":
            tpl.add(key, f"File:{vals[0].split(':')[-1]}")
        elif pid=="P625":
            tpl.add(key, vals[0])
        else:
            tpl.add(key, "; ".join(sorted(set(vals))))
    return str(code)

# ── Mongo helpers ───────────────────────────────────────────────────────
CLAIM_PATH = "claims.P31.mainsnak.datavalue.value.id"

def buddhist_temples(col):
    """Yield docs where P31 == Q5393308."""
    q = { CLAIM_PATH: TARGET_QID }
    for doc in col.find(q):
        title = (doc.get("shinto_titles") or doc.get("page_title") or doc.get("title"))
        if not title: continue
        yield title, doc.get("id") or doc.get("qid") or doc.get("QID")

# ── Main loop ───────────────────────────────────────────────────────────

def main():
    # Mongo connection
    col = MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages = list(buddhist_temples(col))
    print(f"Found {len(pages)} Buddhist temples in Mongo")

    # MediaWiki connection
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    for title, qid in pages:
        page = site.pages[title]
        if not page.exists:
            print(f"✗ {title} missing – skipped")
            continue

        props = wd_get_props(qid, PROPS)
        newtxt = patch_infobox(page.text(), props)
        if newtxt == page.text():
            print(f"• {title} already up‑to‑date")
            continue
        try:
            page.save(newtxt,
                      summary="Bot: sync infobox from Wikidata (P18,P131,P625,P112,P825,P361,P140)",
                      minor=True)
            print(f"✔ Updated {title}")
            time.sleep(THROTTLE)
        except APIError as e:
            print(f"! Failed to save {title}: {e.code}")

if __name__ == "__main__":
    main()
