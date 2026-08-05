#!/usr/bin/env python3
"""
build_description_enrichment_queue.py
======================================
Stage 1 (EN-first) work-file builder for the description enrichment pipeline
(`docs/description_enrichment_pipeline.md`, Emma 2026-07-07): collision groups
— same-labeled items whose standardized descriptions would collide — get
INFORMATIVE, distinguishing ENGLISH descriptions written by the cloud routine
from each item's Wikidata context.

Stage rule: EN-first applies when Japanese has (almost) no descriptions in the
group; groups with substantial ja coverage belong to later stages and are
counted + skipped here. Seed: `modern-quickstatements/description_collision_groups.json`
(built by generate_description_adds.py; groups are per-language but the
membership is language-independent, so cross-language duplicate groups are
merged by member-set).

One work-file per group in `description_enrichment_en/`, carrying per-member
context (labels, municipality, deities, existing-description flags) and an
ANSWERS block the worker fills with one unique English description per line.
`collect_description_enrichment.py` turns answers into Den QuickStatements.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "modern-quickstatements", "description_collision_groups.json")
OUTDIR = os.path.join(ROOT, "description_enrichment_en")
WD_API = "https://www.wikidata.org/w/api.php"
UA = "shintowiki-descenrich/1.0 (https://shinto.miraheze.org; immanuelleleonhart@gmail.com)"
JA_COVERAGE_MAX = 0.10   # stage-1 rule: ja descriptions (nearly) absent
MAX_FILES = 400          # first tranche — the cloud routine paces itself anyway

TASK = (
    "<!-- TASK: every member of this group shares the same label and would get the "
    "same standardized description — they need UNIQUE, informative ENGLISH "
    "descriptions. Using each member's context below (municipality, deities, and "
    "anything you can see on the item), write one short English description per "
    "member that (a) says what it is, (b) distinguishes it from every other member, "
    "and (c) stays in the normal Wikidata description register (no final period; "
    "capitalize only a proper noun, which for these means the leading 'Shinto' — "
    "measured 2026-08-05, the corpus is 11,487 'Shinto …' to 1 'shinto …'), "
    "e.g. 'Shinto shrine in Maebashi, Gunma Prefecture, Japan'. "
    "Municipality-level location is usually the cheapest distinguisher; add the "
    "deity or a local place-name when members share a municipality. Fill each line "
    "of the ANSWERS block after its QID. Leave a line EMPTY if you cannot find "
    "anything distinguishing. Do NOT edit Wikidata yourself — a collector turns "
    "answers into QuickStatements later. -->"
)


def _get(ids):
    url = WD_API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "ids": "|".join(ids),
        "props": "labels|descriptions|claims", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["entities"]
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def fetch_items(qids):
    out = {}
    qids = sorted(set(qids))
    for i in range(0, len(qids), 50):
        out.update(_get(qids[i:i + 50]))
        time.sleep(0.3)
    return out


def main():
    groups = json.load(open(SEED, encoding="utf-8"))
    # merge per-language duplicates of the same member-set
    merged = {}
    for g in groups:
        key = tuple(sorted(g["items"]))
        merged.setdefault(key, g)
    print(f"{len(groups)} seed groups -> {len(merged)} distinct member-sets")

    os.makedirs(OUTDIR, exist_ok=True)
    # fetch everything once (members + one hop of P131/P825 targets)
    all_members = [q for key in merged for q in key]
    items = fetch_items(all_members)
    targets = set()
    for e in items.values():
        for prop in ("P131", "P825"):
            for c in e.get("claims", {}).get(prop, [])[:4]:
                v = c["mainsnak"].get("datavalue", {}).get("value", {})
                if isinstance(v, dict) and v.get("id"):
                    targets.add(v["id"])
    names = fetch_items(targets)

    def lab(q, lang="en"):
        e = names.get(q) or items.get(q) or {}
        L = e.get("labels", {})
        return (L.get(lang, {}) or L.get("ja", {})).get("value", q)

    written = skipped_ja = 0
    for key, g in sorted(merged.items(), key=lambda kv: -len(kv[0])):
        if written >= MAX_FILES:
            break
        members = list(key)
        ja_covered = sum(1 for q in members
                         if "ja" in items.get(q, {}).get("descriptions", {}))
        if members and ja_covered / len(members) > JA_COVERAGE_MAX:
            skipped_ja += 1
            continue
        gid = members[0]
        path = os.path.join(OUTDIR, f"{gid}.wiki")
        if os.path.exists(path):
            continue
        lines = [
            f"<!-- GROUP: {g['lang']}|{g['label']} | proposed-collides: {g['proposed']} -->",
            "<!-- STAGE: EN-first (docs/description_enrichment_pipeline.md) -->",
            "<!-- ANSWERS:",
        ]
        for q in members:
            lines.append(f"{q}: ")
        lines.append("-->")
        lines.append(TASK)
        lines.append("")
        lines.append("== Members ==")
        for q in members:
            e = items.get(q, {})
            en = e.get("labels", {}).get("en", {}).get("value", "")
            ja = e.get("labels", {}).get("ja", {}).get("value", "")
            en_d = e.get("descriptions", {}).get("en", {}).get("value", "")
            munis = [lab(c["mainsnak"]["datavalue"]["value"]["id"])
                     for c in e.get("claims", {}).get("P131", [])[:2]
                     if c["mainsnak"].get("datavalue")]
            deities = [lab(c["mainsnak"]["datavalue"]["value"]["id"])
                       for c in e.get("claims", {}).get("P825", [])[:4]
                       if c["mainsnak"].get("datavalue")]
            bits = [f"en={en!r}", f"ja={ja!r}"]
            if munis:
                bits.append("in " + " / ".join(munis))
            if deities:
                bits.append("deities: " + ", ".join(deities))
            if en_d:
                bits.append(f"EXISTING en desc: {en_d!r}")
            lines.append(f"* [[d:{q}]] — " + " | ".join(bits))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        written += 1
    print(f"{written} stage-1 work-files -> {OUTDIR} "
          f"(groups deferred to later stages for ja coverage: {skipped_ja})")


if __name__ == "__main__":
    main()
