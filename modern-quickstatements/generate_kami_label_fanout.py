#!/usr/bin/env python3
"""
generate_kami_label_fanout.py
=============================
Give every kami item we created the same romanised label in mul, en, en-us, fr and es.

Emma, 2026-10-08, queue item: review every kami item we created and give each the English
label form of batch #289889 (Yodohime-no-Mikoto / Ohobehime no Mikoto / Takeminakata Okami):
the same romanised label in mul, en, en-us, fr and es, plus its ja label (which every created
item already has).

The items are the 191 in `deity_creates.state` (created from deity_creates.txt), plus whatever
Inochi Shrine (Q141677508) is dedicated to (P825) once that deity exists.

The label text for an item is its English label if it has one (61 had one, added by hand),
otherwise its line in `kami_readings.tsv` (written for the other 126; Emma: "You write the
readings"). A language is emitted only where the item has NO label in it, so a label someone
already set is never overwritten.

One SPARQL query per run. GENERATOR ONLY: writes `kami_label_fanout.txt`, an ATOMIC_FILES
drip file; never edits Wikidata.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import io
import json
import os
import sys

import wdqs_transport
from shinto_miraheze.qs_value import qs_escape

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "deity_creates.state")
READINGS = os.path.join(HERE, "kami_readings.tsv")
OUTPUT = os.path.join(HERE, "kami_label_fanout.txt")

INOCHI_SHRINE = "Q141677508"
LANGS = ("mul", "en", "en-us", "fr", "es")


def created_qids(path=STATE):
    with io.open(path, encoding="utf-8") as fh:
        return sorted(set(json.load(fh).values()))


def load_readings(path=READINGS):
    out = {}
    with io.open(path, encoding="utf-8") as fh:
        for raw in fh:
            if raw.startswith("#") or not raw.strip():
                continue
            qid, _ja, label = raw.rstrip("\n").split("\t")
            out[qid] = label.strip()
    return out


def query(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    langs = ", ".join(f'"{l}"' for l in LANGS)
    return f"""SELECT ?k ?lang ?label WHERE {{
  {{ VALUES ?k {{ {values} }} }} UNION {{ wd:{INOCHI_SHRINE} wdt:P825 ?k }}
  OPTIONAL {{ ?k rdfs:label ?label . BIND(LANG(?label) AS ?lang) FILTER(LANG(?label) IN ({langs})) }}
}}"""


def read_labels(rows):
    """{qid: {lang: label}} (an item with no matching label maps to {})."""
    out = {}
    for b in rows:
        q = b["k"]["value"].rsplit("/", 1)[-1]
        rec = out.setdefault(q, {})
        if "lang" in b and "label" in b:
            rec[b["lang"]["value"]] = b["label"]["value"]
    return out


def build_lines(labels, readings):
    lines, missing = [], []
    for q in sorted(labels):
        have = labels[q]
        text = have.get("en") or readings.get(q)
        if not text:
            missing.append(q)
            continue
        for lang in LANGS:
            if lang not in have:
                lines.append(f'{q}|L{lang}|"{qs_escape(text)}"')
    return lines, missing


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    qids = created_qids()
    labels = read_labels(wdqs_transport.query(query(qids)))
    lines, missing = build_lines(labels, load_readings())
    with io.open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(labels)} kami checked; wrote {len(lines)} label line(s) to {OUTPUT}")
    if missing:
        print(f"{len(missing)} with no English label and no reading (add them to kami_readings.tsv): "
              + " ".join(missing))


if __name__ == "__main__":
    main()
