#!/usr/bin/env python3
"""
patch_ill_english_labels_v7.py
──────────────────────────────
* Reads titles from Pages.txt
* Fixes each {{ill}} on ShintoWiki (adds |1=… |comment=… |WD=Q…)
* When the Wikidata item has **no** English label, pushes
      {qid: Q123, proposed_label: "Foo"}   → MongoDB
  (DB: shinto_label_review ‖ Collection: proposed_labels)
"""

from __future__ import annotations
import argparse, logging, pathlib, sys
from typing import Any

import requests, mwclient, mwparserfromhell as mwp
from pymongo import MongoClient

# ─── config ──────────────────────────────────────────────────────────────
SW_USER = "EmmaBot"
SW_PASS = "[REDACTED_SECRET_1]"
MONGO_URI = "mongodb://localhost:27017"   # adjust if needed
DB_NAME = "shinto_label_review"
COLL_NAME = "proposed_labels"
# ─────────────────────────────────────────────────────────────────────────

JA_API = "https://ja.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
SESSION = requests.Session()

# ─── MongoDB connection ──────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
coll = client[DB_NAME][COLL_NAME]

# ─── ShintoWiki helpers ──────────────────────────────────────────────────
SW_SITE = mwclient.Site("shinto.miraheze.org", path="/w/")
SW_SITE.login(SW_USER, SW_PASS)

def shinto_title_status(title: str) -> str:
    pg = SW_SITE.pages[title]
    if not pg.exists:
        return "missing"
    if pg.redirect:
        return "redirect"
    return "exists"

# ─── ja-wiki → Q-ID helper ───────────────────────────────────────────────
def ja_title_to_qid(title: str) -> str | None:
    data = SESSION.get(JA_API, params={
        "action": "query", "titles": title, "prop": "pageprops",
        "ppprop": "wikibase_item", "redirects": 1, "format": "json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops", {}).get("wikibase_item")

# ─── Wikidata read-only helper ───────────────────────────────────────────
def wd_has_en_label(qid: str) -> tuple[bool, str | None]:
    data = SESSION.get(WD_API, params={
        "action": "wbgetentities", "ids": qid, "props": "labels",
        "languages": "en", "format": "json"
    }, timeout=30).json()
    ent = data["entities"].get(qid, {})
    lbl = ent.get("labels", {}).get("en")
    if lbl:
        return True, lbl["value"]
    return False, None

# ─── template helpers ────────────────────────────────────────────────────
def english_display(tpl: mwp.nodes.template.Template) -> str:
    if tpl.has("1"):
        return str(tpl.get("1").value).strip()
    for i, p in enumerate(tpl.params):
        if not p.showkey and i == 0:
            return str(p.value).strip()
    return ""

def ja_title_from_ill(tpl: mwp.nodes.template.Template) -> str | None:
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()

    slots: list[str] = []
    numeric: dict[int, str] = {}
    for p in tpl.params:
        if p.showkey:
            key = str(p.name).strip()
            if key.isdigit():
                numeric[int(key)] = str(p.value).strip()
        else:
            slots.append(str(p.value).strip())
    for idx, val in numeric.items():
        while len(slots) < idx:
            slots.append("")
        slots[idx - 1] = val
    i = 1
    while i < len(slots) - 1:
        if slots[i].lower() == "ja":
            return slots[i + 1]
        i += 2
    return None

def ensure_tail_params(tpl: mwp.nodes.template.Template,
                       en_target: str, qid: str) -> bool:
    wanted = {
        "1": en_target,
        "comment": "changed title based on wikidata",
        "WD": qid
    }
    changed = False
    for key, val in wanted.items():
        for p in tpl.params:
            if p.showkey and str(p.name).strip() == key:
                if str(p.value).strip() != val:
                    p.value = val
                    changed = True
                break
        else:
            tpl.params.append(
                mwp.nodes.template.Parameter(name=key,
                                             value=val,
                                             showkey=True))
            changed = True
    return changed

# ─── per-page driver ─────────────────────────────────────────────────────
def process_page(title: str, dry: bool):
    page = SW_SITE.pages[title]
    if not page.exists:
        logging.warning("! %s missing", title)
        return
    code = mwp.parse(page.text())
    changed = False

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill":
            continue

        # ── NEW: verbose header for every template ───────────────
        en_disp = english_display(tpl)
        logging.info("→ ILL  en:'%s'  raw:'%s'", en_disp, tpl)

        if not en_disp:
            logging.info("· no English display – skip")
            continue
        if shinto_title_status(en_disp) == "exists":
            logging.info("· blue link on ShintoWiki – skip")
            continue

        ja_title = ja_title_from_ill(tpl)
        if not ja_title:
            logging.info("· no ja-pair – skip")
            continue

        qid = ja_title_to_qid(ja_title)
        if not qid:
            logging.info("· %s – no Q-ID", ja_title)
            continue

        has_lbl, wd_en = wd_has_en_label(qid)

        if has_lbl:
            label_to_use = wd_en
            logging.info("· WD has label → |1=%s", wd_en)
        else:
            label_to_use = en_disp
            coll.update_one(
                {"qid": qid},
                {"$set": {"qid": qid, "proposed_label": label_to_use}},
                upsert=True)
            logging.info("· queued   %s → %s", label_to_use, qid)

        if ensure_tail_params(tpl, label_to_use, qid):
            changed = True
            logging.info("· tail params set on template")

    if changed:
        if dry:
            logging.info("· (dry) would save %s", title)
        else:
            page.save(str(code),
                      summary="Bot: append |1= |comment= |WD= in {{ill}}",
                      minor=True)
            logging.info("✓ saved %s", title)

# ─── CLI driver ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="no ShintoWiki edits, but still queue labels")
    ap.add_argument("--pages", default="Pages.txt",
                    help="title list (default Pages.txt)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    titles = [ln.strip() for ln in pathlib.Path(args.pages)
              .read_text(encoding="utf-8").splitlines() if ln.strip()]

    for idx, t in enumerate(titles, 1):
        logging.info("(%d/%d) %s", idx, len(titles), t)
        try:
            process_page(t, args.dry)
        except Exception as e:
            logging.error("! error on %s – %s", t, e)

    queued = coll.count_documents({})
    logging.info("✓ MongoDB now holds %d proposed labels in %s.%s",
                 queued, DB_NAME, COLL_NAME)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted")
