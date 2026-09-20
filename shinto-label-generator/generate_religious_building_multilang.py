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
try:
    from plain_latin_katakana import rules_for_country as _latin_rules_for
except ImportError:                                    # pragma: no cover
    def _latin_rules_for(_qid):
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
# The place's ENGLISH label is fetched too, and is never emitted. It is the only
# thing in the same alphabet as the source string, so it is what tells a
# qualifier that merely repeats the place ("Santa Clara, Vitoria-Gasteiz") from
# one that says something — see `_echoes_place`.
PLACE_LANGS = LANGS + ("en",)
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
    # `"en" not in …` tops up places cached before the English label was needed,
    # the same treatment `p17` got above rather than a full refetch. The key is
    # written even when the place has no English label, so a place that genuinely
    # lacks one is not refetched on every run.
    todo_p = sorted(p for p in places
                    if p not in cache["places"] or "en" not in cache["places"][p])
    for i in range(0, len(todo_p), BATCH):
        for qid, ent in _get(todo_p[i:i + BATCH], "labels",
                             languages="|".join(PLACE_LANGS)).items():
            labs = ent.get("labels") or {}
            row = {lg: labs[lg]["value"] for lg in LANGS if lg in labs}
            row["en"] = (labs.get("en") or {}).get("value")
            cache["places"][qid] = row
        time.sleep(THROTTLE)

    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    return cache


def build(rows, cache):
    """{lang: [qs_line]} plus a reason counter."""
    out = {lg: [] for lg in LANGS}
    seen = {lg: set() for lg in LANGS}
    # ⛔ ONE label line per QID per language. Stage 1 emitted two Commons
    # categories for 6 items -- Q49147232 is both `Engels-Skulptur` and
    # `Wandgrabanlage Richter` -- and while both were refused that cost nothing.
    # Once `de` could read them, both rendered and QuickStatements would have set
    # the item's ja label twice, the second winning arbitrarily.
    seen_qid = {lg: set() for lg in LANGS}
    reasons = {"no P31 mapping": 0, "no P131": 0, "category-shaped": 0,
               "unknown dedication": 0, "no place label": 0, "duplicate": 0,
               "not named as a mosque": 0, "second label for one item": 0,
               "named only by denomination or setting": 0}
    # Not a skip reason — how many of the emitted ja labels came from the
    # transliteration fallback rather than the table. Reported separately so the
    # two paths stay countable.
    read_not_named = 0
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
        place_en = place_labels.get("en")
        # The source language comes from the item's own country, not a guess.
        rules = _rules_for(meta.get("p17"))
        latin_rules = _latin_rules_for(meta.get("p17"))
        # ⛔ The mosque family does not go through `dedication()` at all — that
        # is a Christian saint vocabulary, and gating on it is what gave all 245
        # mosques zero labels. `render_mosque` owns their parse.
        if p31 in morph.MOSQUE_P31:
            if not morph.mosque_parse(label)[4]:
                reasons["not named as a mosque"] += 1
                continue
        elif morph.dedication(label, "ja", rules, latin_rules) is None:
            # ⛔ This gate runs BEFORE `render`, so the transliteration fallback
            # that lives inside `render` has to be asked here too — otherwise it
            # never fires at all, which is what the first run of it did: the
            # output was byte-identical and the skip counter still read
            # "unknown dedication 13470".
            #
            # ⚠ `rules` is now passed to `dedication()`. It used to be called
            # bare, taking its own `"it"` default, so the gate was more permissive
            # than `render` and some items passed it only to be refused a line
            # later. That never changed the output, only the counter.
            if morph.transliterate_dedication(label, "ja", rules, latin_rules,
                                              place_en) is None:
                # ⛔ The gate is ja-shaped and skips the item for ALL languages,
                # so the denomination/setting slot has to be asked here too —
                # it is a TRANSLATION and reaches zh and ko, and 790 items name
                # nothing but their denomination.
                if morph.render_generic(label, p31, "ja", "X") is None:
                    reasons["unknown dedication"] += 1
                    continue
                reasons["named only by denomination or setting"] += 1
            else:
                read_not_named += 1
        for lg in LANGS:
            place = place_labels.get(lg)
            if not place:
                reasons["no place label"] += 1
                continue
            rendered = morph.render(label, p31, lg, place=place,
                                    rules=rules, latin_rules=latin_rules,
                                    place_en=place_en)
            if not rendered:
                continue
            # A duplicate label is the failure this whole design exists to avoid.
            # ⚠ The FIRST item to produce a string keeps it and the rest are
            # dropped — the comment here used to say "neither is emitted", which
            # is not what the code does and never was. It matters because the
            # winner is chosen by iteration order, so a parser change that alters
            # which item is reached first moves a label between two colliding
            # items. Three labels moved that way on 2026-09-19 and read as losses
            # until they were found alive on the other QID.
            if rendered in seen[lg]:
                reasons["duplicate"] += 1
                continue
            if qid in seen_qid[lg]:
                reasons["second label for one item"] += 1
                continue
            seen[lg].add(rendered)
            seen_qid[lg].add(qid)
            out[lg].append('%s|L%s|"%s"' % (qid, lg, rendered))
    reasons["(of which READ, not named)"] = read_not_named
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
    read = reasons.pop("(of which READ, not named)", 0)
    print("\nskipped:")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("  %-20s %6d" % (k, v))
    print("\nja dedications READ rather than named: %d" % read)
    print("\nOn the daily drip via select_label_proposals.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
