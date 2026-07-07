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
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_description_fixes import (  # noqa: E402
    CLASSES, sparql, pref_labels, infer_templates)

OUT = os.path.join(HERE, "description_adds.txt")


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
    """{qid: pref_label_or_None} for items with label@lang but no desc@lang."""
    q = f"""
    SELECT ?item WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      FILTER NOT EXISTS {{ ?item schema:description ?d . FILTER(LANG(?d) = "{lang}") }}
    }}
    """
    out = {b["item"]["value"].rsplit("/", 1)[-1]: None for b in sparql(q)}
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
            out[b["item"]["value"].rsplit("/", 1)[-1]] = b["prefLabel"]["value"]
        time.sleep(1)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "shinto-label-generator"))
    from language_registry import COVERED
    covered = set(COVERED)
    lines, report = [], []
    for cls, extra in CLASSES:
        counts = langs_with_label_no_desc(cls, extra)
        time.sleep(1)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            corpus = desc_corpus(cls, extra, lang)
            time.sleep(1)
            pref_t, gen = infer_templates(corpus, pref_labels(lang))
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, NO inferable template — skipped")
                continue
            targets = targets_with_pref(cls, extra, lang)
            added = 0
            for qid, pref in sorted(targets.items()):
                new = (pref_t.replace("{pref}", pref) if (pref_t and pref) else gen)
                if not new:
                    continue
                esc = new.replace('"', '""')
                lines.append(f'{qid}|D{lang}|"{esc}"')
                added += 1
            report.append(f"{cls} {lang}: targets={counts[lang]} add-lines={added} "
                          f"pref_template={bool(pref_t)}")
    lines = sorted(set(lines))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} description-add lines -> {OUT}")
    for r in report:
        print(" ", r)


if __name__ == "__main__":
    main()
