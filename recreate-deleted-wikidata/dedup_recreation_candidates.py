#!/usr/bin/env python3
"""Broad dedup sweep over the recreation candidates (Emma 2026-07-06) — catch items
that already have a live Wikidata item so we don't recreate duplicates (like Akama
Shrine → Q712617, which slipped the ja-sitelink dedup because it had no ja langlink).

For each recreation candidate (typed, not already flagged) search Wikidata by its
Japanese label and, as a fallback, its English label. Flag a duplicate only on an
EXACT label match (high precision — a live item whose label is byte-identical to the
candidate's ja kanji / en name is almost certainly the same entity). Writes
``enrichment.possible_existing`` so the candidate drops out of the recreation set and
into the relink path. Read-only Wikidata (throttled, 429-bail). Dry-run by default;
``--apply`` writes the flags.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import glob
import io
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
WD = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT
THROTTLE = 0.2


def _has_cjk(s):
    return any("぀" <= c <= "ヿ" or "㐀" <= c <= "鿿" or "豈" <= c <= "﫿" for c in s)


def exact_hit(term, lang):
    """First search hit whose label EXACTLY equals `term` → (qid, label, desc), else None."""
    if not term:
        return None
    for attempt in range(4):
        r = requests.get(WD, params={"action": "wbsearchentities", "search": term,
                                     "language": lang, "uselang": lang, "type": "item",
                                     "limit": "6", "format": "json"},
                         headers={"User-Agent": UA}, timeout=40)
        if r.status_code == 429:
            print("  [429] bailing"); sys.exit(2)
        if r.status_code >= 500:
            time.sleep(2 * (attempt + 1)); continue
        r.raise_for_status()
        for h in r.json().get("search", []):
            if h.get("label", "") == term:
                return h["id"], h.get("label", ""), h.get("description", "")
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    flagged = checked = 0
    for f in sorted(glob.glob(os.path.join(ITEMS, "Q*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        enr = r.get("enrichment") or {}
        if not r.get("recreation_candidate") or not enr.get("p31") or enr.get("possible_existing"):
            continue
        ll = (r.get("fandom") or {}).get("langlinks") or {}
        ja = ll.get("ja") if ll.get("ja") and _has_cjk(ll.get("ja")) else ""
        en = r.get("recovered_label") or ""
        checked += 1
        hit = (exact_hit(ja, "ja") if ja else None) or exact_hit(en, "en")
        time.sleep(THROTTLE)
        if hit:
            qid, lab, desc = hit
            flagged += 1
            print(f"  DUP {en} ({ja}) → {qid} '{lab}' — {desc[:40]}")
            if args.apply:
                r.setdefault("enrichment", {})["possible_existing"] = [
                    {"qid": qid, "label": lab,
                     "note": f"exact-label dedup match ({desc[:60]}) — relink, do not recreate"}]
                json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False,
                          indent=2, sort_keys=True)
    print(f"\n{'APPLIED' if args.apply else 'DRY-RUN'}: {flagged} duplicate(s) found of "
          f"{checked} checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
