#!/usr/bin/env python3
"""sync_kofun_infobox.py
------------------------
Populate or patch **{{Infobox ancient site}}** for every page that is *instance
of* **Kofun (Q1141225)** in your `shinto_wiki` MongoDB.

Properties synced from Wikidata → infobox field mapping
------------------------------------------------------
P18   → image
P131  → location                (JP municipality / prefecture label)
P625  → coordinates             ({{Coord|…}} inline,title)
P112  → builder                 (ill‐style link)
P149  → architectural_styles    (ill link)
P547  → commemorates            (ill or qid link)  [infobox uses |commemorates]
P361  → part_of                 (ill link)
P580  → built                   (earliest year at least)

Other parameters remain untouched.

Run:
    pip install mwclient mwparserfromhell pymongo requests
    python sync_kofun_infobox.py
"""
# ── CONFIG ────────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4  # seconds between edits

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"

TARGET_QID = "Q1141225"  # kofun
PROPS = [
    "P18",  # image
    "P131", # located in adm. unit
    "P625", # coordinates
    "P112", # builder (founded by)
    "P149", # architectural style
    "P547", # commemorates
    "P361", # part of
    "P580", # start time / built
]
WD2INFOBOX = {
    "P18" : "image",
    "P131": "location",
    "P625": "coordinates",
    "P112": "builder",
    "P149": "architectural_styles",
    "P547": "commemorates",
    "P361": "part_of",
    "P580": "built",
}

# -------------------------------------------------------------------------
import os, re, time, json, requests, datetime
from typing import Dict, List, Any
import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str,str] = {}

# ── Wikidata helpers ─────────────────────────────────────────────────────

def wd_label(wid:str) -> str:
    if wid in LABEL_CACHE: return LABEL_CACHE[wid]
    data = requests.get(WD_API, params={
        "action":"wbgetentities","ids":wid,
        "props":"labels","languages":"en|ja","format":"json"}, timeout=20).json()
    ent = data["entities"].get(wid, {})
    lbl = ent.get("labels", {}).get("en", {}).get("value") or wid
    LABEL_CACHE[wid] = lbl
    return lbl


def wd_get_props(qid:str, props:List[str]) -> Dict[str,List[str]]:
    ent = requests.get(WD_API, params={
        "action":"wbgetentities","ids":qid,
        "props":"claims","languages":"en|ja","format":"json"}, timeout=20).json()
    ent = ent["entities"].get(qid, {})
    out = {p: [] for p in props}

    for pid in props:
        for stmt in ent.get("claims", {}).get(pid, []):
            dv = stmt["mainsnak"].get("datavalue", {})
            if not dv: continue
            typ = dv["type"]; val = dv["value"]
            if typ == "wikibase-entityid":
                wid = val["id"]
                lbl = wd_label(wid)
                out[pid].append(f"{{{{ill|{lbl}|qid={wid}}}}}")
            elif typ == "string":
                out[pid].append(val)
            elif typ == "time" and pid == "P580":
                # take year only
                iso = val["time"].lstrip("+")
                year = iso.split("-")[0]
                out[pid].append(year)
            elif typ == "globecoordinate":
                lat, lon = val["latitude"], val["longitude"]
                out[pid].append(
                    f"{{{{Coord|{lat}|N|{lon}|E|region:JP_type:landmark|display=inline,title}}}}")
    return out

# ── Infobox patcher ──────────────────────────────────────────────────────
INFO_REGEX = re.compile(r"Infobox\s+ancient\s+site", re.I)

def patch_infobox(wikitext:str, data:Dict[str,List[str]]) -> str:
    code = mwp.parse(wikitext)
    tpl = next((t for t in code.filter_templates() if INFO_REGEX.match(str(t.name))), None)
    if not tpl:
        tpl = mwp.nodes.Template("Infobox ancient site")
        code.insert(0, tpl)

    for pid, vals in data.items():
        if not vals: continue
        field = WD2INFOBOX[pid]
        if pid == "P18":
            tpl.add(field, f"File:{vals[0].split(':')[-1]}")
        elif pid == "P625":
            tpl.add("coordinates", vals[0])
        elif pid == "P580":
            tpl.add(field, vals[0])
        else:
            tpl.add(field, "; ".join(sorted(set(vals))))
    return str(code)

# ── Mongo helpers ───────────────────────────────────────────────────────
CLAIM_PATH = "claims.P31.mainsnak.datavalue.value.id"

def kofun_pages(col):
    for doc in col.find({CLAIM_PATH: TARGET_QID}):
        title = (doc.get("shinto_titles") or doc.get("page_title") or doc.get("title"))
        if not title: continue
        qid = doc.get("id") or doc.get("qid") or doc.get("QID")
        yield title, qid

# ── Main loop ───────────────────────────────────────────────────────────

def main():
    col = MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages = list(kofun_pages(col))
    print(f"Found {len(pages)} kofun pages in Mongo")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    for title,qid in pages:
        page = site.pages[title]
        if not page.exists:
            print(f"✗ {title} missing – skipped")
            continue

        props = wd_get_props(qid, PROPS)
        newtext = patch_infobox(page.text(), props)
        if newtext == page.text():
            print(f"• {title} up-to-date")
            continue
        try:
            page.save(newtext,
                      summary="Bot: sync infobox from Wikidata (P18,P131,P625,P112,P149,P547,P361,P580)",
                      minor=True)
            print(f"✔ Updated {title}")
            time.sleep(THROTTLE)
        except APIError as e:
            print(f"! Failed {title}: {e.code}")

if __name__ == "__main__":
    main()
