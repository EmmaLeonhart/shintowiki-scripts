#!/usr/bin/env python3
"""
generate_description_fixes.py
==============================
Description-without-label cleanup (Emma 2026-07-07, [[Open questions]]).

Problem: shrines/temples carry a description in language X but no label in X
(≈10k items; almost all id + uk). A stale description blocks later label adds:
the label+description pair must be unique, and the description is supposed to
be the deduplicator. Rule: fix the DESCRIPTION first (standardized form), and
only then may label-adding QS touch the item.

Method (data-driven, never invented):
  * per (class, language), the standardized description is inferred from the
    corpus of EXISTING descriptions on that class's items: the modal generic
    form, plus a prefecture template ("… di Prefektur {pref}, Jepang"-style)
    when ≥ PREF_SUPPORT existing descriptions contain the item's own
    prefecture label — i.e. we reuse the community's own standard form.
  * a target item (desc@X, no label@X) gets the prefecture form when its
    prefecture label@X is known, else the generic modal; items whose
    description already equals the target form are skipped (self-draining).

Ordering guarantee: these lines only CHANGE descriptions. Label adds continue
to come from the shinto-label-generator drip; they fail harmlessly on
uniqueness collisions until the description here has landed, then succeed —
so "description first, then label" holds per item without cross-file
coordination.

Output: description_fixes.txt — `Qxxx|Dxx|"…"` lines (capped at ~100/day in
direct_daily_edits via FILE_DAILY_CAPS, interspersed with the main drip).
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "shinto-label-generator"))
from language_registry import COVERED  # noqa: E402

OUT = os.path.join(HERE, "description_fixes.txt")
WDQS = "https://query-main.wikidata.org/sparql"
UA = "shintowiki-descfix/1.0 (https://shinto.miraheze.org; immanuelleleonhart@gmail.com)"

# (class QID, extra pattern) — same classes the label pipelines cover
CLASSES = [
    ("Q845945", ""),                                   # Shinto shrine
    ("Q5393308", "?item wdt:P17 wd:Q17 ."),            # Buddhist temple (Japan)
]
PREF_SUPPORT = 5      # min corpus descriptions containing the prefecture label
GENERIC_SUPPORT = 3   # min corpus frequency for the generic modal form


def sparql(query):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        return json.load(r)["results"]["bindings"]


def langs_with_targets(cls, extra):
    q = f"""
    SELECT ?lang (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d .
      BIND(LANG(?d) AS ?lang)
      FILTER NOT EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l) = ?lang) }}
    }} GROUP BY ?lang
    """
    return {b["lang"]["value"]: int(b["n"]["value"]) for b in sparql(q)}


def corpus_and_targets(cls, extra, lang):
    """[(qid, desc, has_label, pref_label_or_None)] for every item of cls with desc@lang."""
    q = f"""
    SELECT ?item ?d ?hasLabel ?prefLabel WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
      BIND(EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}") }} AS ?hasLabel)
      OPTIONAL {{ ?item wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ;
                  rdfs:label ?prefLabel . FILTER(LANG(?prefLabel) = "{lang}") }}
    }}
    """
    out = {}
    for b in sparql(q):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        # one row per item; prefer the row that has a prefecture label
        pref = b.get("prefLabel", {}).get("value")
        if qid not in out or (pref and not out[qid][2]):
            out[qid] = (b["d"]["value"], b["hasLabel"]["value"] == "true", pref)
    return out


def infer_templates(items):
    """(pref_template_or_None, generic_or_None) from existing descriptions."""
    pref_forms, generic = Counter(), Counter()
    for desc, _has, pref in items.values():
        if pref and pref in desc:
            pref_forms[desc.replace(pref, "{pref}")] += 1
        else:
            generic[desc] += 1
    pref_t = next((t for t, n in pref_forms.most_common(1) if n >= PREF_SUPPORT), None)
    gen = next((d for d, n in generic.most_common(1) if n >= GENERIC_SUPPORT), None)
    return pref_t, gen


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    covered = set(COVERED)
    lines, report = [], []
    for cls, extra in CLASSES:
        counts = langs_with_targets(cls, extra)
        time.sleep(1)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            items = corpus_and_targets(cls, extra, lang)
            time.sleep(1)
            pref_t, gen = infer_templates(items)
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, NO inferable template — skipped")
                continue
            fixed = skipped = 0
            for qid, (desc, has_label, pref) in sorted(items.items()):
                if has_label:
                    continue
                new = (pref_t.replace("{pref}", pref) if (pref_t and pref) else gen)
                if not new or new == desc:
                    skipped += 1
                    continue
                esc = new.replace('"', '""')
                lines.append(f'{qid}|D{lang}|"{esc}"')
                fixed += 1
            report.append(f"{cls} {lang}: targets={counts[lang]} fix-lines={fixed} "
                          f"already-standard={skipped} pref_template={bool(pref_t)}")
    lines = sorted(set(lines))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} description-fix lines -> {OUT}")
    for r in report:
        print(" ", r)


if __name__ == "__main__":
    main()
