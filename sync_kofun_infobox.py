#!/usr/bin/env python3
"""sync_kofungun_infobox.py  –  v1.2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Scope change**: *only* works on **kofun‑gun groups** (`P31 = Q11411019`).

Changes
-------
* TARGET_QID is now a single list `["Q11411019"]` – plain kofun (`Q1141225`) are
  left untouched.
* Added **P527 → has part(s)** and mapped it to the infobox field
  `part_of` (the closest available parameter in *Infobox ancient site*).
* Keeps earlier additions: P1435 → `Historic Site`, P571 fallback to `built`.
* When the script encounters both P361 *and* P527 it concatenates them under
  the single `part_of` line.
"""

# ── CONFIG ───────────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4

MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "shinto_wiki"
COLLECTION = "shinto_raw"

TARGET_QIDS = ["Q11411019"]  # kofun-gun only

PROPS = [
    "P18", "P131", "P625", "P112", "P149", "P547", "P361", "P527",
    "P580", "P571", "P1435"
]
WD2INFOBOX = {
    "P18"  : "image",
    "P131" : "location",
    "P625" : "coordinates",
    "P112" : "builder",
    "P149" : "architectural_styles",
    "P547" : "commemorates",
    "P361" : "part_of",            # parent complex
    "P527" : "part_of",            # has part(s) – list of individual kofun
    "P580" : "built",              # start time
    "P571" : "built",              # inception (fallback)
    "P1435": "Historic Site",      # heritage designation
}

# ── imports ────────────────────────────────────────────────────────────
import re, time, json, requests
from typing import Dict, List, Set
import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str, str] = {}

# ---------- label helpers ---------------------------------------------

def wd_label(wid: str) -> str:
    if wid in LABEL_CACHE:
        return LABEL_CACHE[wid]
    data = requests.get(WD_API, params={
        "action": "wbgetentities", "ids": wid,
        "props": "labels", "languages": "en|ja", "format": "json"
    }, timeout=20).json()
    lab = (
        data["entities"].get(wid, {})
        .get("labels", {})
        .get("en", {})
        .get("value", wid)
    )
    LABEL_CACHE[wid] = lab
    return lab


def ill(wid: str) -> str:
    return f"{{{{ill|{wd_label(wid)}|qid={wid}}}}}"

# ---------- date helper -----------------------------------------------

def fmt_year(val: dict) -> str:
    return val["time"].lstrip("+").split("-")[0]

# ---------- fetch properties ------------------------------------------

def wd_props(qid: str) -> Dict[str, List[str]]:
    ent = requests.get(WD_API, params={
        "action": "wbgetentities", "ids": qid,
        "props": "claims", "languages": "en|ja", "format": "json"
    }, timeout=20).json()["entities"].get(qid, {})

    out: Dict[str, List[str]] = {p: [] for p in PROPS}

    for pid in PROPS:
        for st in ent.get("claims", {}).get(pid, []):
            dv = st["mainsnak"].get("datavalue", {})
            if not dv:
                continue
            typ, val = dv.get("type"), dv.get("value")

            if pid in ("P580", "P571") and typ == "time":
                out[pid].append(fmt_year(val))
            elif pid == "P625" and typ == "globecoordinate":
                out[pid].append(
                    f"{{{{Coord|{val['latitude']}|N|{val['longitude']}|E|region:JP_type:landmark|display=inline,title}}}}"
                )
            elif typ == "wikibase-entityid":
                out[pid].append(ill(val["id"]))
            elif typ == "string":
                out[pid].append(val)
    return out

# ---------- infobox patcher -------------------------------------------
INFO_RX = re.compile(r"Infobox\s+ancient\s+site", re.I)


def patch(wikitext: str, data: Dict[str, List[str]]) -> str:
    code = mwp.parse(wikitext)
    tpl = next((t for t in code.filter_templates() if INFO_RX.match(str(t.name))), None)
    if not tpl:
        tpl = mwp.nodes.Template("Infobox ancient site")
        code.insert(0, tpl)

    for pid, vals in data.items():
        if not vals:
            continue
        field = WD2INFOBOX[pid]
        value = "; ".join(sorted(set(vals)))
        if pid == "P18":
            value = f"File:{vals[0].split(':')[-1]}"
        # Merge if field already present
        if tpl.has(field):
            existing = str(tpl.get(field).value).strip()
            if value not in existing:
                tpl.get(field).value = existing + "; " + value
        else:
            tpl.add(field, value)
    return str(code)

# ---------- Mongo selector --------------------------------------------
CLAIM_PATH = "claims.P31.mainsnak.datavalue.value.id"


def kofungun_pages(col):
    for doc in col.find({CLAIM_PATH: {"$in": TARGET_QIDS}}):
        title = (
            doc.get("shinto_titles")
            or doc.get("page_title")
            or doc.get("title")
        )
        if not title:
            continue
        qid = doc.get("id") or doc.get("qid") or doc.get("QID")
        yield title, qid

# ---------- main loop --------------------------------------------------

def main():
    col = MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages = list(kofungun_pages(col))
    print(f"{len(pages)} kofun‑gun pages to sync")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    for title, qid in pages:
        page = site.pages[title]
        if not page.exists:
            print("✗", title)
            continue
        new_text = patch(page.text(), wd_props(qid))
        if new_text == page.text():
            print("•", title)
            continue
        try:
            page.save(
                new_text,
                summary="Bot: sync Kofun‑gun infobox from Wikidata (image/location/coords/etc.)",
                minor=True,
            )
            print("✔", title)
            time.sleep(THROTTLE)
        except APIError as e:
            print("!", title, e.code)


if __name__ == "__main__":
    main()
