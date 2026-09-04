#!/usr/bin/env python3
"""STAGE 2: short name / gender / date of birth, for kami that ALREADY carry P1035.

Emma 2026-07-16:

    "The short name is the difficult thing to derive for something with an
     honorific. The way our query system should work, just to be clear, is that we
     add the honorifics based off of the simple process. Once we have finished, a
     secondary query thing queries the [kami] that has the honorific suffixes and
     then adds in the short name, the gender, the date of birth, all that stuff.
     In this sense, it's a stateful thing where the short name isn't even added
     until the honorific is known."

    "every single kami has exactly one short name, and the short name is the hard
     part to derive. Once the short name is derived, all that happens at this
     point is it just adds in stuff. It just adds in."

STAGE 1 is generate_shinto_honorifics.py -> P1035 only.
STAGE 2 (this file) reads that P1035 back off Wikidata and emits:

    <kami>|P1813|ja:"<label minus the honorific>"|P2440|"<romaji minus the honorific>"
    <kami>|P21|Q24238356          # ONLY where the kami has no P21
    <kami>|P569|novalue           # ONLY where the kami has no P569

Why two stages and not one pass: the short name is stripped using the honorific
the item ACTUALLY CARRIES, confirmed by a fresh query — not a guess re-derived
alongside it. This is the repo's standing rule (CLAUDE.md: "Add-first,
remove-later via SPARQL (two scripts, never one) ... script 2 only acts on items
where a fresh SPARQL query *confirms the add already landed*"), and it means a
wrong P1035 can be fixed on-wiki and the short name follows, instead of both
being wrong together.

ONE short name per kami, even when it carries several honorifics ("There's going
to be one short name regardless of how many honorifics there are"): the LONGEST
honorific that its ja label actually ends with decides.

Vocabulary is hardcoded — imported from stage 1's HONORIFIC_FORMS. The honorific
items are never queried ("Everything is hard-coded into this logic").

Output: shinto_short_names.txt (an ATOMIC_FILES entry -> the daily drip).
"""
import os
import re
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from generate_shinto_honorifics import (
    EXCLUDED, HONORIFIC_FORMS, KAMI_CLASS, UNKNOWN,
    derive_from_english, kana_rendaku, rendaku_variants, sparql,
)
# Straight from the shared module rather than re-exported through honorifics, which
# does not use it itself. The copy it used to re-export escaped quotes but not
# backslashes, so a short name containing one emitted an invalid QS value.
#
# This file now needs its own bootstrap above: it used to reach `shinto_miraheze`
# only as a side effect of the honorifics import running one first, which
# `test_sys_path_bootstrap_ordering` refuses -- `python <file>` puts the script's
# own directory on sys.path[0], never the repo root.
from shinto_miraheze.qs_value import qs_escape

# stdout is already wrapped for utf-8 by the stage-1 import above.

_here = os.path.dirname(os.path.abspath(__file__))
OUTFILE = os.path.join(_here, "shinto_short_names.txt")
REVIEWFILE = os.path.join(_here, "shinto_short_names_judgement.txt")


def forms_for(qid):
    """(ja forms, romaji forms) for one honorific, longest-first, rendaku included."""
    f = HONORIFIC_FORMS[qid]
    ja = set(f["ja"])
    en = set(f["en"])
    for x in list(en):
        en |= rendaku_variants(x)
    for x in list(ja):
        if not re.search(r"[一-龯]", x):
            ja.add(kana_rendaku(x))
    return (sorted(ja, key=len, reverse=True), sorted(en, key=len, reverse=True))


def load_targets():
    """Kami that ALREADY carry P1035 — the state stage 1 created."""
    rows = sparql(f"""
    SELECT ?k ?h ?ja ?en (BOUND(?sn) AS ?hasSN) (BOUND(?g) AS ?hasP21) (BOUND(?d) AS ?hasP569) WHERE {{
      ?k wdt:P31/wdt:P279* wd:{KAMI_CLASS} ; wdt:P1035 ?h .
      ?k rdfs:label ?ja FILTER(LANG(?ja) = "ja")
      OPTIONAL {{ ?k rdfs:label ?en FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?k wdt:P1813 ?sn }}
      OPTIONAL {{ ?k wdt:P21   ?g }}
      OPTIONAL {{ ?k wdt:P569  ?d }}
    }}""")
    out = {}
    for r in rows:
        q = r["k"]["value"].split("/")[-1]
        rec = out.setdefault(q, {
            "ja": r["ja"]["value"],
            "en": r.get("en", {}).get("value", ""),
            "honorifics": set(),
            "has_sn": r["hasSN"]["value"] == "true",
            "has_p21": r["hasP21"]["value"] == "true",
            "has_p569": r["hasP569"]["value"] == "true",
        })
        rec["honorifics"].add(r["h"]["value"].split("/")[-1])
    return out


def main():
    print("Stage 2 — kami that already carry P1035 (state written by stage 1)...")
    targets = load_targets()
    print(f"  {len(targets)} kami with a P1035")

    # every (ja form, honorific) the item actually carries, longest-first
    lines, judgement = [], []
    n_sn = 0
    for qid, k in sorted(targets.items()):
        if qid in EXCLUDED:
            continue
        carried = [h for h in k["honorifics"] if h in HONORIFIC_FORMS]
        if not carried:
            judgement.append((qid, k["ja"], k["en"], "P1035 value is outside HONORIFIC_FORMS"))
            continue

        # ONE short name: the LONGEST carried honorific its ja label ends with.
        best_form, best_h = None, None
        for h in carried:
            ja_forms, _ = forms_for(h)
            for f in ja_forms:
                if k["ja"].endswith(f) and len(k["ja"]) > len(f):
                    if best_form is None or len(f) > len(best_form):
                        best_form, best_h = f, h
        if not best_form:
            judgement.append((qid, k["ja"], k["en"],
                              "carries P1035 but the ja label ends with none of its forms"))
            continue

        # の/ノ is a particle — part of the label, not the name, "often implied".
        short_ja = k["ja"][: -len(best_form)].rstrip("のノ乃之・ ")
        if not short_ja:
            judgement.append((qid, k["ja"], k["en"], "stripping leaves no short name"))
            continue

        if not k["has_sn"]:
            _, en_forms_all = zip(*(forms_for(h) for h in carried)) if carried else ((), ())
            all_en = sorted({e for fs in en_forms_all for e in fs}, key=len, reverse=True)
            idx = {e.lower(): h for h in carried for e in forms_for(h)[1]}
            _, romaji = derive_from_english(k["en"], idx, all_en)
            if romaji:
                lines.append(f'{qid}|P1813|ja:"{qs_escape(short_ja)}"|P2440|"{qs_escape(romaji)}"')
            else:
                lines.append(f'{qid}|P1813|ja:"{qs_escape(short_ja)}"')
            n_sn += 1

        # ADD-ONLY — never clobber a real gender/date (Emma: "only where absent").
        if not k["has_p21"]:
            lines.append(f"{qid}|P21|{UNKNOWN}")
        if not k["has_p569"]:
            lines.append(f"{qid}|P569|novalue")

    with open(OUTFILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    with open(REVIEWFILE, "w", encoding="utf-8") as f:
        f.write("# Stage 2 residue — Emma's judgement calls. Never emitted.\n\n")
        for qid, ja, en, why in sorted(judgement):
            f.write(f"{qid}\tja={ja}\ten={en}\t{why}\n")

    print(f"\nwrote {OUTFILE}: {len(lines)} lines ({n_sn} short names)")
    print(f"wrote {REVIEWFILE}: {len(judgement)} judgement calls")


if __name__ == "__main__":
    main()
