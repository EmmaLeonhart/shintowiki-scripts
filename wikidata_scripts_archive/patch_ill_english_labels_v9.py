#!/usr/bin/env python3
"""
patch_ill_english_labels_v9.py
──────────────────────────────
* Everything v7 did, plus …
* When a {{ill}} has no Wikidata item at all, write/merge a document in
      DB: shinto_label_review ‖ Collection: missing_ills
  keyed by the ja‑label found in the template.
"""

from __future__ import annotations
import argparse, logging, pathlib, sys
from typing import Any, Dict, Tuple, List

import requests, mwclient, mwparserfromhell as mwp
from pymongo import MongoClient

# ─── config ──────────────────────────────────────────────────────────────
SW_USER = "EmmaBot"
SW_PASS = "[REDACTED_SECRET_1]"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "shinto_label_review"
COLL_PROPOSED = "proposed_labels"   # unchanged
COLL_MISSING  = "missing_ills"      # ← NEW
# ─────────────────────────────────────────────────────────────────────────

JA_API = "https://ja.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
SESSION = requests.Session()

# ─── MongoDB connection ──────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
coll_prop = client[DB_NAME][COLL_PROPOSED]
coll_miss = client[DB_NAME][COLL_MISSING]

# ─── ShintoWiki helpers ──────────────────────────────────────────────────
SW_SITE = mwclient.Site("shinto.miraheze.org", path="/w/")
SW_SITE.login(SW_USER, SW_PASS)

import re
QID_RE = re.compile(r"^Q\d{1,9}$")

def qid_from_template(tpl: mwp.nodes.template.Template) -> str | None:
    for p in tpl.params:
        if not p.showkey:
            continue
        key = str(p.name).strip().lower()
        if key in {"qid", "wd"}:
            val = str(p.value).strip()
            if QID_RE.match(val):
                return val
    return None

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

def parse_ill_languages(tpl: mwp.nodes.template.Template) -> Dict[str, str]:
    """
    Return {lang_code: label} for every language present in the {{ill}}.
    Works with numbered, named and positional params.
    """
    values: list[str] = []
    numeric: dict[int, str] = {}
    named_langs: dict[str, str] = {}

    for p in tpl.params:
        if p.showkey:
            name = str(p.name).strip()
            # explicit lang parameter (ja=, fr= …) – ignore maintenance keys
            if len(name) == 2 and name.isalpha():
                named_langs[name] = str(p.value).strip()
            elif name.isdigit():
                numeric[int(name)] = str(p.value).strip()
        else:
            values.append(str(p.value).strip())

    # merge numbered params back into values
    for idx, val in numeric.items():
        while len(values) < idx:
            values.append("")
        values[idx - 1] = val

    langs: dict[str, str] = {}

    if values:
        langs["en"] = values[0]  # first positional is always en

    i = 1
    while i < len(values) - 1:
        code = values[i].strip().lower()
        if len(code) == 2 and code.isalpha():
            langs[code] = values[i + 1].strip()
        i += 2

    # named parameters override/extend
    langs.update(named_langs)
    return {k: v for k, v in langs.items() if v}

def ensure_tail_params(tpl: mwp.nodes.template.Template,
                       en_target: str, qid: str) -> bool:
    wanted = {"1": en_target, "comment": "changed title based on wikidata", "WD": qid}
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
                mwp.nodes.template.Parameter(name=key, value=val, showkey=True))
            changed = True
    return changed

# ─── page‑level helpers ──────────────────────────────────────────────────
def translated_page_info(code: mwp.wikicode.Wikicode) -> Tuple[str | None, int | None]:
    """
    Returns (ja_title, rev_id) from {{translated page|ja|TITLE|version=123…}}
    If not present, both are None.
    """
    for tpl in code.filter_templates(recursive=False):
        if tpl.name.strip().lower() in {"translated page", "translatedpage"}:
            # param 2 (positional index 1) is the title
            ja_title = None
            if tpl.has(2):
                ja_title = str(tpl.get(2).value).strip()
            # version or oldid
            rev = None
            if tpl.has("version"):
                rev = int(str(tpl.get("version").value).strip())
            elif tpl.has("oldid"):
                rev = int(str(tpl.get("oldid").value).strip())
            return ja_title, rev
    return None, None

def upsert_missing_ill(ja_label: str,
                       lang_labels: Dict[str, str],
                       shinto_page: str,
                       trans_title: str | None,
                       trans_rev: int | None) -> None:
    """
    Merge / insert a record keyed by the ja label.
    """
    # Build update operators
    add_to_set: Dict[str, Any] = {}
    push: Dict[str, Any] = {}

    for lang, lbl in lang_labels.items():
        add_to_set[f"labels.{lang}"] = lbl

    ref_obj = {"page": shinto_page}
    if trans_title:
        ref_obj["translated_from"] = trans_title
    if trans_rev:
        ref_obj["rev"] = trans_rev
    push["occurrences"] = ref_obj

    coll_miss.update_one(
        {"ja": ja_label},
        {
            "$setOnInsert": {"ja": ja_label},
            "$addToSet": add_to_set,
            "$push": push
        },
        upsert=True
    )

# ─── per-page driver ─────────────────────────────────────────────────────
def process_page(title: str, dry: bool):
    page = SW_SITE.pages[title]
    if not page.exists:
        logging.warning("! %s missing", title)
        return
    code = mwp.parse(page.text())
    trans_title, trans_rev = translated_page_info(code)
    changed = False

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill":
            continue

        en_disp = english_display(tpl)
        if not en_disp:
            continue
        if shinto_title_status(en_disp) == "exists":
            continue

        # NEW: if the template already names a Wikidata item, skip it entirely
        qid_in_tpl = qid_from_template(tpl)
        if qid_in_tpl:
            logging.debug("… skipping {{ill}} with explicit QID %s on %s", qid_in_tpl, title)
            continue

        ja_title = ja_title_from_ill(tpl)
        if not ja_title:
            continue

        qid = ja_title_to_qid(ja_title)
        if qid:
            has_lbl, wd_en = wd_has_en_label(qid)
            label_to_use = wd_en if has_lbl else en_disp

            if not has_lbl:
                coll_prop.update_one(
                    {"qid": qid},
                    {"$set": {"qid": qid, "proposed_label": label_to_use}},
                    upsert=True)

            if ensure_tail_params(tpl, label_to_use, qid):
                changed = True
            continue  # handled by existing logic

        # no Wikidata item found → record in missing_ills
        lang_labels = parse_ill_languages(tpl)
        upsert_missing_ill(
            ja_label=ja_title,
            lang_labels=lang_labels,
            shinto_page=title,
            trans_title=trans_title,
            trans_rev=trans_rev
        )


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

    queued_prop = coll_prop.count_documents({})
    queued_miss = coll_miss.count_documents({})
    logging.info("✓ %d proposed labels in %s.%s",
                 queued_prop, DB_NAME, COLL_PROPOSED)
    logging.info("✓ %d missing ill entries in %s.%s",
                 queued_miss, DB_NAME, COLL_MISSING)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted")
