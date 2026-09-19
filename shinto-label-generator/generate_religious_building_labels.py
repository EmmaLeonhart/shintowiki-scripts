"""
generate_religious_building_labels.py
=====================================
Religious buildings that are NOT Shinto shrines or Buddhist temples — churches,
cathedrals, chapels, mosques, synagogues, and the non-Japanese temple tree — get an
English label copied from their Wikimedia Commons category, provided that category is
in Latin script (Emma 2026-07-10: "We always copy the commons category name to the
English label, assuming that the commons category is in Latin script … for mosques and
churches and synagogues").

⛔ **THIS SCRIPT IS PAUSED, AND ITS OUTPUT DOES NOT GO TO WIKIDATA.**
Paused 2026-09-17 (`df9303510`), Emma: *"Earlier sessions underestimated the difficulty
and used wikimedia commons as the only source like it was somehow authoritative."*
Measured over all 22,548 lines, 67% carry no English type word and many are plain German
or Italian — `Kirche Rehden`, `Jerusalemkirche`, `San Giovanni Battista`. **The script
check only ever asked whether the characters were Latin, never whether the string was
English.** The output lives in `paused/religious_building_en.txt`, outside the directory
`select_label_proposals.py` globs, and this generator is unwired from CI. See
`paused/README.md`; `tests/test_paused_labels_stay_out_of_the_drip.py` pins it.

The file is retained because **stage 2 reads it as its input corpus** —
`generate_religious_building_multilang.py` derives the ja/zh/ko labels from these
strings, and those are on the drip. So the file is live as a corpus and dead as output.

⭐ **DO NOT "drop the Latin-script gate and transliterate Arabic/Hebrew/Devanagari".**
It was a 2026-09-19 queue item and it is wrong four separate ways, measured rather than
argued — recorded here so it is not re-derived a third time:

* **The gate rejects 2 items.** The 2026-07-11 run: 22,644 candidates, **2** non-Latin
  Commons names skipped, ~94 producing no clean label. 0.009%, not a population.
* **Arab-world mosques are already selected** — 16 of them (Saudi 4, Egypt 3, Palestine
  2, UAE 2, Iran 2, Oman, Tunisia, Yemen), plus **451 synagogues**. The claim that they
  are "never selected" is false; the few that go no further are refused *downstream* by
  `plain_latin_katakana.rules_for_country`, which is a different and deliberate thing.
* **Arabic and Hebrew do not romanise derivably.** Both scripts omit short vowels, so a
  transliterator invents them. Measured with `aksharamukha`, which this repo already
  depends on: `مسجد النور` (Masjid al-Nur) → `masajada alanav̈ara`, and
  `בית הכנסת הגדול` (Beit HaKnesset HaGadol) → `vĕyt hĕk͟hnĕst hĕgdĕvl`. That is the
  confident-wrong failure `romance_katakana.rules_for_country` and
  `plain_latin_katakana`'s refusals exist to prevent. (Devanagari *is* clean —
  `श्री राम मन्दिर` → `śrī rāma mandira` — but see the first point for the population.)
* **It widens the intake that got this script paused.** An English label transliterated
  out of an Arabic Commons category is further from "an authoritative English source"
  than the German strings that stopped it.

This is **stage 1** of the religious-building label pipeline. Stage 2 is
`generate_religious_building_multilang.py`, which exists.

Non-destructive: only items with NO English label yet are emitted. Latin-script only —
a Commons category in Cyrillic/Arabic/CJK/etc. is skipped, never guessed.

Output: paused/religious_building_en.txt   (<qid>|Len|"<label>")

    python generate_religious_building_labels.py             # full run (paged)
    python generate_religious_building_labels.py --limit 500 # sample
"""
import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
# wdqs_transport lives in modern-quickstatements/, so a plain `import
# wdqs_transport` does not reach it from here.
_usys.path.insert(0, _uos.path.join(_uar, "modern-quickstatements"))

import wdqs_transport

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
# ⛔ `paused/`, NOT `quickstatements/`. Membership of that directory is the whole
# submit decision — `select_label_proposals.py` globs it and pools the raw lines — and
# the 2026-09-17 pause moved this file out of it. The constant still said
# `quickstatements/`, so a hand-run of this script would have silently put 22,548 paused
# labels straight back on the drip.
OUT = os.path.join(HERE, "paused", "religious_building_en.txt")
# query.wikidata.org has been 429-outaged since 2026-07-06; the SPLIT endpoint
# query-main serves everything except scholarly articles (repo policy).
WDQS = "https://query-main.wikidata.org/sparql"
# hand-built literal, not the canonical agent
# was: UA = f"ShintoWikiReligiousBuilding/1.0 ({contact('wikidata')})"
UA = WIKIDATA_USER_AGENT

# Building classes to cover — churches/cathedrals/chapels, mosques, synagogues.
# Deliberately NOT Shinto shrine (Q845945) or Buddhist temple (Q5393308): those
# have their own romaji pipeline (commons_normalize + the shrine multilang gen).
CLASSES = [
    "Q16970",    # church building
    "Q2977",     # cathedral
    "Q108325",   # chapel
    "Q32815",    # mosque
    "Q34627",    # synagogue
]

# The temple family, added 2026-09-18. Emma: *"Temples that aren't Japanese go in the
# 10%."* So the line is NATIONALITY, not religion — a Japanese Buddhist temple is Shinto
# and belongs to the 90% pipeline (generate_temple_en_labels.py); a mandir, a wat or a
# gurdwara joins the church/mosque/synagogue population here.
#
# ⛔ A FLAT LIST OF QIDS IS THE WRONG SHAPE HERE, and the first draft of this was one.
# Emma: *"my assumption is that the p31 subclasses are treated as their own subclasses
# anyway with divergent logic."* The five classes above are siblings and enumerate
# correctly; the temple tree does not. Q44539 `temple` has a real subclass hierarchy under
# it — Hindu temple, Buddhist temple, wat, gurdwara, Jain temple, temple of Confucius —
# and enumerating twelve of them by hand means every subclass nobody typed out is silently
# out of scope, with no symptom. So the SELECTION walks `P279*` from the root, and the
# DIVERGENT part lives where it belongs: `religious_building_morphemes.TYPES` gives each
# subclass its own type word, and a subclass with no entry emits nothing rather than
# inheriting a word that would be wrong for it.
#
# ⚠ WHAT THIS IS WORTH, measured 2026-09-18 rather than assumed. At this stage's gate —
# has a Commons category, has no English label — the enumerated temple family was 534
# items, 210 of them Japanese Buddhist. The class list is not what limits it; the GATE is.
# Hindu temple is 16,587 items on Wikidata and 5 of them pass, because an Indian temple
# article is titled in English and the item already carries an English label. 6,788 Hindu
# temples have an en label, no ja label and a P131 place — reachable by stage 2 and
# invisible to it, because stage 2 reads only this stage's output file. That is a real and
# separate gap; it is recorded in DEVLOG.md 2026-09-18 and is not this query's job.
TEMPLE_ROOT = "Q44539"      # temple — walked with P279*, not enumerated
TEMPLE_COUNTRY_EXCLUDED = "Q17"   # Japan: those temples are the 90% pipeline's

_BRACKETS = re.compile(r"\s*[（(\[][^）)\]]*[）)\]]\s*$")


def is_latin_script(text):
    """True if every letter in `text` is a Latin-script letter.

    Punctuation, digits, spaces and combining marks are ignored; a single
    non-Latin letter (Cyrillic/Arabic/Greek/CJK/…) disqualifies the name — that
    is the 'assuming the commons category is in Latin script' gate.
    """
    saw_letter = False
    for ch in text:
        if ch.isalpha():
            saw_letter = True
            if not unicodedata.name(ch, "").startswith("LATIN"):
                return False
    return saw_letter


def commons_to_english(commons_name):
    """Commons category name → English label, or None if not Latin-script.

    Copies the name (Emma's rule) after stripping a leading 'Category:' and a
    trailing bracketed disambiguator; commas are kept (they are part of church
    names like 'St Mary's Church, Oxford'). Latin-script only.
    """
    name = (commons_name or "").strip()
    if name.startswith("Category:"):
        name = name[len("Category:"):].strip()
    name = _BRACKETS.sub("", name).strip()
    name = re.sub(r"\s+", " ", name)
    if not name or not is_latin_script(name):
        return None
    return name


# ─────────────────────────── network ───────────────────────────

def _wdqs(query):
    """One WDQS query, through the shared transport.

    ⚠ `post=True` preserves what this already did and why: the VALUES batches make
    the URL too long for a GET. The transport classifies 414/431 as fatal rather
    than retryable for the same reason.

    It had no retry at all — a truncated body ended the run — and no throttle. Both
    now come from the transport.
    """
    return wdqs_transport.query(query, timeout=180, post=True)


def fetch_candidates(limit=None):
    """[(qid, commons)] for buildings of CLASSES, plus the whole P279* temple tree, that have a Commons
    category but no English label. Paged to stay under WDQS result caps.

    The temple branch is a UNION rather than one VALUES list because only it carries the
    country filter: a temple in Japan is the 90% pipeline's, a church in Japan is ours."""
    out, offset, page = [], 0, 4000
    values = " ".join("wd:" + c for c in CLASSES)
    while True:
        q = f"""SELECT ?item ?commons WHERE {{
          {{
            VALUES ?cls {{ {values} }}
            ?item wdt:P31 ?cls ; wdt:P373 ?commons .
          }} UNION {{
            ?cls wdt:P279* wd:{TEMPLE_ROOT} .
            ?item wdt:P31 ?cls ; wdt:P373 ?commons .
            FILTER NOT EXISTS {{ ?item wdt:P17 wd:{TEMPLE_COUNTRY_EXCLUDED} }}
          }}
          FILTER NOT EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l)="en") }}
        }} ORDER BY ?item LIMIT {page} OFFSET {offset}"""
        rows = _wdqs(q)
        for b in rows:
            out.append((b["item"]["value"].rsplit("/", 1)[-1], b["commons"]["value"]))
            if limit and len(out) >= limit:
                return out[:limit]
        if len(rows) < page:
            break
        offset += page
        time.sleep(1)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    cands = fetch_candidates(args.limit)
    print(f"{len(cands)} religious buildings with a Commons category and no English label")
    lines, skipped = [], []
    for qid, commons in cands:
        label = commons_to_english(commons)
        if not label:
            skipped.append((qid, commons))
            continue
        esc = label.replace('"', '')
        lines.append(f'{qid}|Len|"{esc}"')
    lines = sorted(set(lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} English labels -> {OUT} "
          f"(Commons names skipped: {len(skipped)})")
    # NAME them, do not just count them. The bare count is what made "the gate is why
    # there are no Arab-world mosques" unfalsifiable without a fresh WDQS sweep: the
    # 2026-07-11 run recorded "2 skipped" and nothing about WHICH 2, so a later session
    # read the number as a population. Printing them makes it checkable from one run.
    for qid, commons in skipped:
        print(f"  skipped {qid}  {commons}")


if __name__ == "__main__":
    main()
