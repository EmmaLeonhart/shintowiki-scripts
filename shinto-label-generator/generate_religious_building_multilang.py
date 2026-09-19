#!/usr/bin/env python3
"""
generate_religious_building_multilang.py
========================================
Stage 2 of the religious-building label pipeline: **ja / zh / ko** labels for
churches, chapels, mosques, synagogues and the rest of the place-of-worship tree.

Emma's decisions, 2026-09-17, in the order they were made:

* **ja/zh/ko only.** English is left alone — stage 1's Commons-derived
  `religious_building_en.txt` is paused (`paused/README.md`) and is not re-derived
  here.
* **Morphemes, not per-item translation.** *"We look at common words and morphemes
  across all of the things lol."* The tables live in
  `religious_building_morphemes.py`; measured coverage is **24.6%** of the corpus
  (5,540 of 22,548) across **96** distinct dedications.
* **Place first, possessive** — `<place>の<dedication><type>`.
* **Everything in the tree**, destroyed buildings included.
* **Output to `quickstatements/`** — ordinary generated output, on the daily
  drip like every other language file. It sat in `paused/` until 2026-09-18;
  Emma: *"why is all of this shit paused instead of part of the pipeline as
  expected"*. There was no defect in it, and a review directory nobody is
  obliged to read is the human-gate CLAUDE.md warns against.

## Why the place is mandatory, and not a nicety

The first version composed dedication + type only. Measured over the corpus that
produced **36 distinct outputs for 2,392 labels — 99.6% of them colliding**, with
**515** different Madonna churches all becoming 聖母教会 and 201 becoming
聖ニコラオス教会. For this population the "name" IS the dedication, and hundreds of
buildings share it; what separates them is where they are.

`P131` carries that and is present on **100%** of a 200-item sample, with **192
distinct places for 200 items** — so it very nearly disambiguates on its own.
`render()` therefore refuses to emit without a place.

⚠ **The place must have its own label in the target language**, and often does not:
measured over those 192 places, **ja 44.8%, zh 56.2%, ko 24.5%**, with 42.2%
carrying none of the three. Those items are skipped rather than transliterated —
generating a place name is a decision this pipeline does not make.

## Reading, not querying

WDQS answered 504 then 429 on 2026-09-17 and `wdqs_transport` bailed per repo
policy, so this uses the **read API** (`wbgetentities`, 50 ids per call) rather
than SPARQL. Results are cached to `religious_building_cache.json` so a re-run
costs nothing; delete the cache to refresh.

Usage:
    python generate_religious_building_multilang.py [--limit N] [--refresh]
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import religious_building_morphemes as morph  # noqa: E402
try:
    from romance_katakana import rules_for_country as _rules_for
except ImportError:                                    # pragma: no cover
    def _rules_for(_qid):
        return None

import os as _uos, sys as _usys  # noqa: E402
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(
        _uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

API = "https://www.wikidata.org/w/api.php"
SRC = os.path.join(HERE, "paused", "religious_building_en.txt")
OUTDIR = os.path.join(HERE, "quickstatements")
CACHE = os.path.join(HERE, "religious_building_cache.json")
LANGS = ("ja", "zh", "ko")
BATCH = 50
THROTTLE = 1.0          # read API, not WDQS; still paced.

_LINE = re.compile(r'^(Q\d+)\|Len\|"(.+)"\s*$')


def source_labels():
    """[(qid, english_label)] from the paused stage-1 file."""
    out = []
    if not os.path.exists(SRC):
        return out
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            m = _LINE.match(line.strip())
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def _get(ids, props, languages=None):
    params = {"action": "wbgetentities", "format": "json",
              "ids": "|".join(ids), "props": props}
    if languages:
        params["languages"] = languages
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("entities", {}) or {}


def _claim_id(entity, prop):
    ids = _claim_ids(entity, prop)
    return ids[0] if ids else None


def _claim_ids(entity, prop):
    """EVERY entity-valued statement on that property, in the order served.

    P31 needs all of them. The selection query (`generate_religious_building_labels.py`)
    matches `wdt:P31` against 5 building classes, so every item in the population is one
    of those -- but an item commonly carries a DESIGNATION statement beside it and
    Wikidata serves the designation first:

        Q106484005  P31 = [Q2319498 architectural landmark, Q16970 church building]

    Keeping only `[0]` recorded the landmark and lost the church. That is what put 1,749
    items in the "no P31 mapping" bucket, 1,412 of them under `architectural landmark`, and
    it read as junk in the population rather than as a dropped statement. Sampled 40 of
    them on 2026-09-18: 40 of 40 carry a selection class.
    """
    out = []
    for c in (entity.get("claims") or {}).get(prop, []):
        try:
            out.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            continue
    return out


def building_type(meta, types):
    """The item's P31 that `types` knows, or None.

    Reads `p31s` when present and falls back to the legacy single `p31`, so a cache
    written before this fix still resolves rather than refetching 22,542 items.
    """
    for qid in (meta.get("p31s") or ([meta["p31"]] if meta.get("p31") else [])):
        if qid in types:
            return qid
    return None


def fetch(qids, refresh=False):
    """{qid: {"p31":..., "p131":...}} plus {place_qid: {lang: label}}."""
    cache = {"items": {}, "places": {}}
    if os.path.exists(CACHE) and not refresh:
        with open(CACHE, encoding="utf-8") as fh:
            cache = json.load(fh)
    cache.setdefault("items", {})
    cache.setdefault("places", {})

    # Also top up items cached before P17 was fetched, rather than forcing a
    # full refetch of all 22,542 for one added property. Same treatment for `p31s`:
    # an entry whose single cached `p31` is not a building type is the one the
    # first-statement-only bug mangled, so refetch exactly those and leave the rest.
    todo = [q for q in qids
            if q not in cache["items"]
            or "p17" not in cache["items"][q]
            or ("p31s" not in cache["items"][q]
                and building_type(cache["items"][q], morph.TYPES) is None)]
    for i in range(0, len(todo), BATCH):
        for qid, ent in _get(todo[i:i + BATCH], "claims").items():
            p31s = _claim_ids(ent, "P31")
            cache["items"][qid] = {"p31s": p31s,
                                   "p31": p31s[0] if p31s else None,
                                   "p131": _claim_id(ent, "P131"),
                                   "p17": _claim_id(ent, "P17")}
        time.sleep(THROTTLE)

    places = {v["p131"] for v in cache["items"].values() if v.get("p131")}
    todo_p = sorted(p for p in places if p not in cache["places"])
    for i in range(0, len(todo_p), BATCH):
        for qid, ent in _get(todo_p[i:i + BATCH], "labels",
                             languages="|".join(LANGS)).items():
            labs = ent.get("labels") or {}
            cache["places"][qid] = {lg: labs[lg]["value"]
                                    for lg in LANGS if lg in labs}
        time.sleep(THROTTLE)

    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    return cache


def build(rows, cache):
    """{lang: [qs_line]} plus a reason counter."""
    out = {lg: [] for lg in LANGS}
    seen = {lg: set() for lg in LANGS}
    reasons = {"no P31 mapping": 0, "no P131": 0, "category-shaped": 0,
               "unknown dedication": 0, "no place label": 0, "duplicate": 0}
    for qid, label in rows:
        meta = cache["items"].get(qid) or {}
        if morph.is_category_shaped(label):
            reasons["category-shaped"] += 1
            continue
        p31 = building_type(meta, morph.TYPES)
        if not p31:
            reasons["no P31 mapping"] += 1
            continue
        if not meta.get("p131"):
            reasons["no P131"] += 1
            continue
        place_labels = cache["places"].get(meta["p131"]) or {}
        # The source language comes from the item's own country, not a guess.
        rules = _rules_for(meta.get("p17"))
        if morph.dedication(label, "ja") is None:
            reasons["unknown dedication"] += 1
            continue
        for lg in LANGS:
            place = place_labels.get(lg)
            if not place:
                reasons["no place label"] += 1
                continue
            rendered = morph.render(label, p31, lg, place=place,
                                    rules=rules)
            if not rendered:
                continue
            # A duplicate label is the failure this whole design exists to avoid;
            # if two items still collide, neither is emitted.
            if rendered in seen[lg]:
                reasons["duplicate"] += 1
                continue
            seen[lg].add(rendered)
            out[lg].append('%s|L%s|"%s"' % (qid, lg, rendered))
    return out, reasons


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None,
                    help="Only the first N source items (for a sample run).")
    ap.add_argument("--refresh", action="store_true",
                    help="Ignore the cache and refetch.")
    args = ap.parse_args()

    rows = source_labels()
    if not rows:
        print("No source labels at %s — nothing to do." % SRC)
        return 0
    if args.limit:
        rows = rows[:args.limit]
    print("source items: %d" % len(rows))

    cache = fetch([q for q, _ in rows], refresh=args.refresh)
    out, reasons = build(rows, cache)

    os.makedirs(OUTDIR, exist_ok=True)
    for lg in LANGS:
        path = os.path.join(OUTDIR, "religious_building_%s.txt" % lg)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out[lg]) + ("\n" if out[lg] else ""))
        print("  %-3s %6d lines -> quickstatements/%s"
              % (lg, len(out[lg]), os.path.basename(path)))
    print("\nskipped:")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("  %-20s %6d" % (k, v))
    print("\nOn the daily drip via select_label_proposals.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
