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
import re
import sys
import time
import urllib.parse
import urllib.request
from shinto_miraheze.ua_contact import contact

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "modern-quickstatements", "description_collision_groups.json")
OUTDIR = os.path.join(ROOT, "description_enrichment_en")
WD_API = "https://www.wikidata.org/w/api.php"
UA = f"shintowiki-descenrich/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"
JA_COVERAGE_MAX = 0.10   # stage-1 rule: ja descriptions (nearly) absent

# A description this pipeline is allowed to replace. Anything else is Emma's own
# writing and must be left alone.
#
# WHY THIS EXISTS (found 2026-08-05, before anything was delivered). The Den
# command SETS a description, overwriting whatever is there. 15 of the 22 lines
# staged in description_enrichment_en.txt would have replaced a hand-written
# annotation with location boilerplate:
#
#   'The 1111th Shrine of the Engishiki Jinmyōchō (Ronsha)'
#       -> 'Shinto shrine in Kōfu, Yamanashi Prefecture, Japan'
#   'Ronsha 3 of Yaahino Shrine'
#       -> 'Shinto shrine in Azai district, Ōmi Province, Japan'
#   'A candidate shrine for Nakagawa Shrine'
#       -> 'Shinto shrine in Japan, candidate for Nakagawa Shrine'
#
# Those encode the shrine's position in the 927 register and WHICH disputed entry
# it is a candidate for, and which numbered Ronsha it is. None of that is
# recoverable from a location. This is the failure CLAUDE.md names directly:
# an unfamiliar pattern on this data is signal, not corruption.
#
# TIGHTENED 2026-08-05 on Emma's correction: "We were never supposed to enrich
# English descriptions that aren't equal to Shinto shrine in Japan."
#
# The first version of this gate matched any `Shinto shrine in X`, on the
# reasoning that a prefecture-level description is a placeholder worth improving.
# That was wrong. 'Shinto shrine in Shizuoka Prefecture, Japan' is not a
# placeholder — it states the prefecture, which is real information somebody put
# there. Rewriting it to a municipality is churn on this pipeline's authority,
# not enrichment.
#
# MEASURED, and the result decides the rule's practical meaning: of 14,300
# English descriptions on Shinto shrine items, **ZERO** are exactly
# "Shinto shrine in Japan". 11,369 are some other `Shinto shrine in X` and 2,931
# are something else entirely. So the exact-match arm below is dead in the
# current corpus by design, and the rule reduces to: this pipeline may only give
# a description to an item that HAS none.
GENERIC_DESC = "shinto shrine in japan"


def needs_a_description(existing):
    """True if this pipeline may write a description for the item.

    Absent -> yes; nothing is destroyed by filling an empty field. Exactly the
    generic "Shinto shrine in Japan" -> yes, it carries no information. Anything
    else -> NO, including every `Shinto shrine in <somewhere>` form: naming the
    prefecture IS the information, and this pipeline does not get to overrule it.
    """
    if not existing or not existing.strip():
        return True
    return existing.strip().lower() == GENERIC_DESC


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
    # Inside main(): rebinding at module scope replaces the caller's stdout,
    # and collect_description_enrichment.py imports needs_a_description from
    # here. Same fix as generate_soja_only.py / build_label_typo_review_queue.py.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
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

    written = skipped_ja = skipped_protected = 0
    for key, g in sorted(merged.items(), key=lambda kv: -len(kv[0])):
        if written >= MAX_FILES:
            break
        members = list(key)
        ja_covered = sum(1 for q in members
                         if "ja" in items.get(q, {}).get("descriptions", {}))
        if members and ja_covered / len(members) > JA_COVERAGE_MAX:
            skipped_ja += 1
            continue
        # Members whose existing description is Emma's own writing are shown as
        # context but never asked for — see needs_a_description(). A group with
        # nothing left to ask is not written at all.
        askable = [q for q in members
                   if needs_a_description(items.get(q, {})
                                          .get("descriptions", {})
                                          .get("en", {}).get("value", ""))]
        if not askable:
            skipped_protected += 1
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
        for q in askable:
            lines.append(f"{q}: ")
        lines.append("-->")
        lines.append(TASK)
        lines.append("")
        lines.append("== Members ==")
        for q in members:      # context lists EVERY member, askable or not —
            e = items.get(q, {})   # the protected ones are what a new description
            en = e.get("labels", {}).get("en", {}).get("value", "")   # must differ from
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
          f"(groups deferred to later stages for ja coverage: {skipped_ja}; "
          f"groups skipped because every member already has a hand-written "
          f"description: {skipped_protected})")


if __name__ == "__main__":
    main()
