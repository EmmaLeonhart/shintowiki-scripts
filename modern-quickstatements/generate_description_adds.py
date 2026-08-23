#!/usr/bin/env python3
"""
generate_description_adds.py
=============================
The description MAKER (Emma 2026-07-07, [[Open questions]]): shrines/temples
that HAVE a label in language X but no description in X get the standardized
description — "only after the label exists". Sibling of
generate_description_fixes.py (which handles the inverse desc-without-label
case as desc-then-label pairs) and reuses its machinery: templates inferred
from each language's own existing-description corpus (modal generic +
prefecture form), per-item prefectures fetched in VALUES batches.

Backlog at build time: 40,794 items across 54 covered languages
(fr 23,216 / id 14,197 / zh family ~2,100 / long tail). Languages whose
corpus supports no template are skipped, never guessed.

Output: description_adds.txt — plain `Qxxx|Dxx|"…"` lines (uncapped in the
daily drip; simple single adds, unlike the ordered pairs).
"""
import io
import os
import json
import re
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from generate_description_fixes import (  # noqa: E402
    CLASSES, sparql, pref_labels, infer_templates)

OUT = os.path.join(HERE, "description_adds.txt")
GROUPS = os.path.join(HERE, "description_collision_groups.json")


def langs_with_label_no_desc(cls, extra):
    q = f"""
    SELECT ?lang (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l .
      BIND(LANG(?l) AS ?lang)
      FILTER NOT EXISTS {{ ?item schema:description ?d . FILTER(LANG(?d) = ?lang) }}
    }} GROUP BY ?lang
    """
    return {b["lang"]["value"]: int(b["n"]["value"]) for b in sparql(q)}


def desc_corpus(cls, extra, lang):
    """{qid: (desc, True, None)} — existing descriptions, for template inference."""
    q = f"""
    SELECT ?item ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
    }}
    """
    return {b["item"]["value"].rsplit("/", 1)[-1]: (b["d"]["value"], True, None)
            for b in sparql(q)}


def targets_with_pref(cls, extra, lang):
    """{qid: [label, pref_label_or_None]} for items with label@lang but no desc@lang."""
    q = f"""
    SELECT ?item ?l WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      FILTER NOT EXISTS {{ ?item schema:description ?d . FILTER(LANG(?d) = "{lang}") }}
    }}
    """
    out = {b["item"]["value"].rsplit("/", 1)[-1]: [b["l"]["value"], None] for b in sparql(q)}
    time.sleep(1)
    qids = sorted(out)
    for i in range(0, len(qids), 150):
        batch = " ".join(f"wd:{x}" for x in qids[i:i + 150])
        pq = f"""
        SELECT ?item ?prefLabel WHERE {{
          VALUES ?item {{ {batch} }}
          ?item wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ;
                rdfs:label ?prefLabel . FILTER(LANG(?prefLabel) = "{lang}")
        }}
        """
        for b in sparql(pq):
            out[b["item"]["value"].rsplit("/", 1)[-1]][1] = b["prefLabel"]["value"]
        time.sleep(1)
    return out


_CLASS_LABELS = {}


def class_label(cls, lang):
    """The class item's own label in this language (cached per class)."""
    if cls not in _CLASS_LABELS:
        import urllib.request
        req = urllib.request.Request(
            f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={cls}"
            f"&props=labels&format=json",
            # was a PLAIN string containing "{contact('wikidata')}" -- the braces shipped
            # verbatim, so this request went out with no contact address at all.
            headers={"User-Agent": WIKIDATA_USER_AGENT})
        _CLASS_LABELS[cls] = json.load(urllib.request.urlopen(req))[
            "entities"][cls].get("labels", {})
    return _CLASS_LABELS[cls].get(lang, {}).get("value")


def existing_pairs(cls, extra, lang):
    """{(label, desc)} already on this class's items in this language — the
    EXTERNAL side of the uniqueness rule (docs/description_enrichment_pipeline.md).
    Scoped to the class: cross-class collisions are overwhelmingly same-class
    (same-named shrines); a full-Wikidata pair sweep is not queryable."""
    q = f"""
    SELECT ?l ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
    }}
    """
    return {(b["l"]["value"], b["d"]["value"]) for b in sparql(q)}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "shinto-label-generator"))
    from language_registry import COVERED
    covered = set(COVERED)
    lines, report, collisions = [], [], []
    for cls, extra in CLASSES:
        counts = langs_with_label_no_desc(cls, extra)
        time.sleep(1)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            corpus = desc_corpus(cls, extra, lang)
            time.sleep(1)
            prefs = pref_labels(lang)
            pref_t, gen = infer_templates(corpus, prefs)
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, NO inferable template — skipped")
                continue
            # CLASS-SPECIFICITY guard: the template must actually SAY what the
            # item is — it must share a content word (≥4 chars) with the
            # class's own Wikidata label in this language ("sanctuaire shinto"
            # / "kuil Shinto" / "buddhistischer Tempel"). Mass-imported junk
            # like "bâtiment de préfecture de X, Japon" shares none and is
            # dropped (2026-07-07/08: two weaker guards let 7-9k junk fr
            # descriptions through; exact cross-class comparison was not
            # enough because each class infers DIFFERENT junk strings).
            cls_label = class_label(cls, lang)
            def _class_true(t):
                if not (t and cls_label):
                    return False
                words = {w for w in re.split(r"\W+", cls_label.lower()) if len(w) >= 4}
                return any(w in t.lower() for w in words)
            if pref_t and not _class_true(pref_t):
                report.append(f"{cls} {lang}: pref template {pref_t!r} lacks class word ({cls_label!r}) — dropped")
                pref_t = None
            if gen and not _class_true(gen):
                report.append(f"{cls} {lang}: generic {gen!r} lacks class word ({cls_label!r}) — dropped")
                gen = None
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, no class-true template — skipped")
                continue
            targets = targets_with_pref(cls, extra, lang)
            time.sleep(1)
            taken = existing_pairs(cls, extra, lang)
            # The uniqueness rule: proposals checked against each other
            # (internal) and against existing pairs (external); colliders are
            # never emitted — they become collision groups for the cloud
            # enrichment pipeline.
            proposals = {}
            for qid, (label, pref) in targets.items():
                new = (pref_t.replace("{pref}", pref) if (pref_t and pref) else gen)
                if new:
                    proposals[qid] = (label, new)
            by_pair = defaultdict(list)
            for qid, pair in proposals.items():
                by_pair[pair].append(qid)
            added = collided = 0
            for pair, qids in sorted(by_pair.items()):
                label, new = pair
                if len(qids) > 1 or pair in taken:
                    collided += len(qids)
                    collisions.append({"lang": lang, "class": cls, "label": label,
                                       "proposed": new, "items": sorted(qids),
                                       "external": pair in taken})
                    continue
                esc = new.replace('"', '""')
                lines.append(f'{qids[0]}|D{lang}|"{esc}"')
                added += 1
            report.append(f"{cls} {lang}: targets={counts[lang]} add-lines={added} "
                          f"collided={collided} pref_template={bool(pref_t)}")
    lines = sorted(set(lines))
    with open(GROUPS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(collisions, f, ensure_ascii=False, indent=1)
    print(f"{len(collisions)} collision groups -> {GROUPS}")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} description-add lines -> {OUT}")
    for r in report:
        print(" ", r)


if __name__ == "__main__":
    main()
