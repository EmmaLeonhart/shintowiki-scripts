#!/usr/bin/env python3
"""Dedup check for the HUMAN recreation candidates against live Wikidata.

Emma 2026-07-06: many of the deleted individuals came from family trees and were
likely ALREADY recreated (she tried to recreate a lot of the family-tree people),
so before recreating any person we must check whether a live Wikidata item already
exists — recreating a duplicate is the failure we most want to avoid.

For each candidate whose enrichment.p31 == Q5 (human), searches Wikidata
(`wbsearchentities`) for its English and Japanese labels, then keeps only hits that
are themselves people (P31 = Q5), recording {qid, label, description} into
`enrichment.possible_existing` + a `_human_dedup_summary.md`. This does NOT decide —
it surfaces probable duplicates for Emma's go/no-go per person. Read-only Wikidata
(throttled, 429-bail); writes only local JSON. Run after enrich_p31.py.
"""
import io
import os
import sys
import glob
import json
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "items")
WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
HUMAN_QID = "Q5"
THROTTLE = 0.25


def _get(params):
    for attempt in range(4):
        try:
            r = requests.get(WD_API, params=params, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429:
                print("  [429] bailing per policy")
                sys.exit(2)
            if r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def search_people(label, lang):
    """Return [qid, ...] items whose label/alias matches `label` in `lang`. Pure
    input→network; caller filters to humans."""
    if not label:
        return []
    r = _get({"action": "wbsearchentities", "search": label, "language": lang,
              "uselang": lang, "type": "item", "limit": "8", "format": "json"})
    time.sleep(THROTTLE)
    if not r:
        return []
    return [h["id"] for h in r.get("search", [])]


def humans_among(qids):
    """Of `qids`, return {qid: {label, description}} for those that are P31=Q5."""
    out = {}
    uniq = sorted(set(qids))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get({"action": "wbgetentities", "ids": "|".join(batch),
                  "props": "claims|labels|descriptions", "languages": "en|ja",
                  "format": "json"})
        time.sleep(THROTTLE)
        if not r:
            continue
        for qid, e in r.get("entities", {}).items():
            p31 = [c["mainsnak"]["datavalue"]["value"]["id"]
                   for c in e.get("claims", {}).get("P31", [])
                   if c["mainsnak"].get("datavalue")]
            if HUMAN_QID not in p31:
                continue
            lab = ((e.get("labels", {}).get("en") or e.get("labels", {}).get("ja")
                    or {}).get("value", ""))
            desc = ((e.get("descriptions", {}).get("en")
                     or e.get("descriptions", {}).get("ja") or {}).get("value", ""))
            out[qid] = {"label": lab, "description": desc}
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    files = sorted(glob.glob(os.path.join(ITEMS_DIR, "Q*.json")))
    rows = []
    checked = flagged = 0
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if not rec.get("recreation_candidate"):
            continue
        enr = rec.setdefault("enrichment", {})
        if enr.get("p31") != HUMAN_QID:
            continue
        checked += 1
        en = rec.get("recovered_label") or (rec.get("fandom") or {}).get("label") or ""
        ja = ((rec.get("fandom") or {}).get("langlinks") or {}).get("ja") or ""
        hits = search_people(en, "en") + search_people(ja, "ja")
        people = humans_among(hits)
        enr["possible_existing"] = [{"qid": q, **v} for q, v in people.items()]
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        if people:
            flagged += 1
        rows.append((rec["qid"], en, ja, people))
        print(f"  {rec['qid']} {en}: {len(people)} possible existing")

    lines = ["# Human recreation candidates — Wikidata dedup check\n",
             f"- Human candidates checked: **{checked}**",
             f"- With ≥1 possible existing Wikidata person: **{flagged}** "
             "(verify per person before recreating — recreating a duplicate is the "
             "failure to avoid)\n",
             "Hits are label/alias matches that are themselves P31=Q5 (human). This "
             "SURFACES probable duplicates; it does not decide. See `dedup_humans.py`.\n",
             "## Per human\n"]
    for qid, en, ja, people in sorted(rows, key=lambda r: (-len(r[3]), r[0])):
        if people:
            hit = "; ".join(f"[{q}] {v['label']} — {v['description']}"
                            for q, v in people.items())
        else:
            hit = "— none found (likely safe to recreate)"
        lines.append(f"- **{en}** ({ja}) `{qid}`: {hit}")
    with open(os.path.join(ITEMS_DIR, "_human_dedup_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nChecked {checked} humans; {flagged} have ≥1 possible existing Wikidata person.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
