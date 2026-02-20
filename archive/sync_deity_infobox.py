#!/usr/bin/env python3
"""sync_deity_infobox.py
========================
Populate / patch **{{Infobox deity}}** for every page whose *instance of*
(`P31`) is any of the standard Shinto-deity Q-IDs.

Added in this version
---------------------
* **P460 → equivalent5**   ← NEW

Run:
    pip install mwclient mwparserfromhell pymongo requests
    python sync_deity_infobox.py
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

DEITY_QIDS = [
    "Q178885",       # deity
    "Q524158",       # kami
    "Q60994492",     # amatsukami
    "Q60995523",     # kunitsukami
    "Q3080343",      # gongen
    "Q5369590",      # myōjin
]

PROPS = [
    "P18", "P21", "P22", "P25", "P26", "P40",
    "P1038", "P1039", "P1049", "P361", "P527", "P2925",
    "P460",                         # ← NEW
]

WD2INFOBOX = {
    "P18"  : "image",
    "P21"  : "gender",
    "P22"  : "parents",
    "P25"  : "parents",
    "P26"  : "consort",
    "P40"  : "offspring",
    "P1038": "relatives",
    "P1039": "relatives",
    "P1049": "venerated_in",  # worshipped by
    "P361" : "member_of",
    "P527" : "attributes",
    "P2925": "deity_of",
    "P460" : "equivalent5",   # ← NEW mapping
}

# ── imports ─────────────────────────────────────────────────────────────
import re, time, json, requests
from typing import Dict, List
import mwclient, mwparserfromhell as mwp
from pymongo import MongoClient
from mwclient.errors import APIError

WD_API = "https://www.wikidata.org/w/api.php"
LABEL_CACHE: Dict[str, str] = {}

# ---------- label helpers ---------------------------------------------

def wd_label(wid: str) -> str:
    if wid in LABEL_CACHE:
        return LABEL_CACHE[wid]
    info = requests.get(
        WD_API,
        params={
            "action": "wbgetentities",
            "ids": wid,
            "props": "labels",
            "languages": "en|ja",
            "format": "json",
        },
        timeout=20,
    ).json()
    lbl = (
        info["entities"]
        .get(wid, {})
        .get("labels", {})
        .get("en", {})
        .get("value", wid)
    )
    LABEL_CACHE[wid] = lbl
    return lbl


def ill(wid: str) -> str:
    return f"{{{{ill|{wd_label(wid)}|qid={wid}}}}}"

# ---------- fetch props -----------------------------------------------

def wd_props(qid: str) -> Dict[str, List[str]]:
    ent = requests.get(
        WD_API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims",
            "languages": "en|ja",
            "format": "json",
        },
        timeout=20,
    ).json()["entities"].get(qid, {})
    out: Dict[str, List[str]] = {p: [] for p in PROPS}
    for pid in PROPS:
        for st in ent.get("claims", {}).get(pid, []):
            dv = st["mainsnak"].get("datavalue", {})
            if not dv:
                continue
            t = dv.get("type")
            v = dv.get("value")
            if t == "wikibase-entityid":
                out[pid].append(ill(v["id"]))
            elif t == "string":
                out[pid].append(v)
    return out

# ---------- infobox patcher -------------------------------------------
INFO_RX = re.compile(r"Infobox\s+deity", re.I)


def patch(text: str, data: Dict[str, List[str]]) -> str:
    code = mwp.parse(text)
    tpl = next(
        (t for t in code.filter_templates() if INFO_RX.match(str(t.name))), None
    )
    if not tpl:
        tpl = mwp.nodes.Template("Infobox deity")
        code.insert(0, tpl)

    for pid, vals in data.items():
        if not vals:
            continue
        field = WD2INFOBOX[pid]
        merged = "; ".join(sorted(set(vals)))
        if pid == "P18":
            merged = f"File:{vals[0].split(':')[-1]}"
        if tpl.has(field):
            existing = str(tpl.get(field).value).strip()
            if merged not in existing:
                tpl.get(field).value = existing + "; " + merged
        else:
            tpl.add(field, merged)
    return str(code)

# ---------- Mongo selector --------------------------------------------
CLAIM = "claims.P31.mainsnak.datavalue.value.id"

def deity_pages(col):
    for d in col.find({CLAIM: {"$in": DEITY_QIDS}}):
        title = d.get("shinto_titles") or d.get("page_title") or d.get("title")
        if not title:
            continue
        qid = d.get("id") or d.get("qid") or d.get("QID")
        yield title, qid

# ---------- main loop --------------------------------------------------

def main():
    col = MongoClient(MONGO_URI)[MONGO_DB][COLLECTION]
    pages = list(deity_pages(col))
    print(f"{len(pages)} deity pages to sync")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)

    for title, qid in pages:
        page = site.pages[title]
        if not page.exists:
            print("✗", title)
            continue
        new = patch(page.text(), wd_props(qid))
        if new == page.text():
            print("•", title)
            continue
        try:
            page.save(
                new,
                summary="Bot: sync Infobox deity from Wikidata (image/gender/relatives/etc.)",
                minor=True,
            )
            print("✔", title)
            time.sleep(THROTTLE)
        except APIError as e:
            print("!", title, e.code)


if __name__ == "__main__":
    main()
