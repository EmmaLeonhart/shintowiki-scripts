#!/usr/bin/env python3
"""sync_shinto_shrine_infobox.py
--------------------------------
Populate / patch **{{Infobox religious building}}** for every page that is
*instance of* **Shinto shrine (Q845945)**.  Mirrors the Buddhist‑temple script
but adds P149 → architecture_style.

Usage:
    pip install mwclient mwparserfromhell pymongo requests
    python sync_shinto_shrine_infobox.py
"""
# ── CONFIG ────────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 0.4      # seconds between edits

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"

TARGET_QID = "Q845945"        # Shinto shrine
PROPS      = [
    "P18",   # image
    "P140",  # religion or worldview
    "P131",  # located in the admin unit
    "P625",  # coordinates
    "P112",  # founded by
    "P825",  # dedicated to
    "P361",  # part of
    "P149",  # architectural style
]
WD2INFOBOX = {
    "P18":  "image",
    "P140": "religious_affiliation",
    "P131": "prefecture",
    "P625": "coordinates",
    "P112": "founded_by",
    "P825": "deity",
    "P361": "part_of",
    "P149": "architecture_style",
}
# ──────────────────────────────────────────────────────────────────────────
import os, time, re, requests, json
from typing import Any, Dict, List
import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str,str] = {}

# ── Wikidata helpers ─────────────────────────────────────────────────────

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
INFONAME = re.compile(r"Infobox\s+religious\s+building", re.I)

def patch_infobox(wikitext:str, data:Dict[str,List[str]]) -> str:
    code = mwp.parse(wikitext)
    tpl = next((t for t in code.filter_templates() if INFONAME.match(str(t.name))), None)
    if not tpl:
        tpl = mwp.nodes.Template("Infobox religious building")
        code.insert(0, tpl)
    for pid, vals in data.items():
        if not vals: continue
        key = WD2INFOBOX[pid]
        if pid=="P18":
            tpl.add(key, f"File:{vals[0].split(':')[-1]}")
        elif pid=="P625":
            tpl.add("coordinates", vals[0])
        else:
            tpl.add(key, "; ".join(sorted(set(vals))))
    return str(code)

# ── Mongo: find shrines ──────────────────────────────────────────────────
CLAIM_PATH = "claims.P31.mainsnak.datavalue.value.id"

def shinto_shrines(col):
    for d in col.find({CLAIM_PATH: TARGET_QID}):
        title = (d.get("shinto_titles") or d.get("page_title") or d.get("title"))
        if not title: continue
        qid = d.get("id") or d.get("qid") or d.get("QID")
        yield title, qid

# ── Main loop ───────────────────────────────────────────────────────────

def main():
    col = MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages = list(shinto_shrines(col))
    print(f"Found {len(pages)} Shinto shrines in Mongo")

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
                      summary="Bot: sync infobox from Wikidata (P18,P131,P625,P112,P825,P361,P140,P149)",
                      minor=True)
            print(f"✔ Updated {title}")
            time.sleep(THROTTLE)
        except APIError as e:
            print(f"! Failed to save {title}: {e.code}")

if __name__ == "__main__":
    main()
