#!/usr/bin/env python3
"""REPORT ONLY — how well commons_normalize reproduces enwiki titles.

Proves the Commons→label normalizer before any Wikidata edit is ever proposed. Fetches
Japanese shrines + temples that have a Commons category, runs the normalizer, and grades
the candidate against the enwiki title (the sample of correct answers) on the CORE reading
— the ` Temple`/` Shrine` house suffix is treated as house-appended, and macron
differences are counted as *acceptable*, never failures (Emma: the least-bad romaji error).

Emits nothing runnable: a markdown report + a machine-readable mismatch dump. No `.txt`, no
QuickStatements, nothing in ATOMIC_FILES. Edits wait until Emma reads the number.

    python report_commons_label_accuracy.py            # fetch live, write the report
    python report_commons_label_accuracy.py --limit N   # cap the fetch (debugging)

Spec: docs/superpowers/specs/2026-07-10-commons-romaji-normalization-design.md
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import commons_normalize
from kana_english import hardcoded_label

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "docs")
UA = USER_AGENT
SPARQL = "https://query-main.wikidata.org/sparql"

SHRINE = "Q845945"
TEMPLE = "Q5393308"
JAPAN = "Q17"

_MACRONS = str.maketrans("āīūēōĀĪŪĒŌ", "aiueoAIUEO")
_PAREN = re.compile(r"\s*\([^)]*\)")

# Classificatory suffixes stripped (repeatedly) to bare the reading stem. Longest first.
# Includes English house forms AND the romaji SHRINE words enwiki keeps untranslated
# (taisha, jingū, -gū …) — "X Grand Shrine" and "X-taisha" must reduce to the same stem.
# Deliberately EXCLUDES the romaji temple suffixes ji/dera/tera/in/an/do/bo: our temple
# candidates keep them exactly as enwiki does ("Kiyomizu-dera"), so they stay on both
# sides, and stripping them would eat real stems (Meiji → Mei).
# Only PURE classificatory suffixes. NOT "hachimangu"/"tenmangu"/"myojin" — those carry
# name material (Hachimangū = Hachiman-deity + gū; strip only the "gu"), and stripping the
# whole word desyncs from a candidate that kept the "hachiman".
_STRIP_SUFFIXES = ("grand shrine", "daijingu", "daijinja", "taisha", "jinja", "jingu",
                   "shrine", "temple", "gu", "sha")


def _mf(s):
    return s.translate(_MACRONS)


def core(label):
    """Bare the reading stem: drop a parenthetical, unify hyphen/space, fold case, strip
    every classificatory suffix (English or romaji-shrine), remove separators, keep macrons.

    This measures whether the *reading* is right. Suffix convention (Grand Shrine vs
    Taisha), hyphenation, and spacing are noise; macrons are handled by `bucket`. A genuine
    reading difference (Ideha vs Dewa) survives because the stems still differ.
    """
    s = _PAREN.sub("", label or "").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip().casefold()
    changed = True
    while changed:
        changed = False
        for tok in _STRIP_SUFFIXES:
            if _mf(s).endswith(tok) and len(s) > len(tok):
                s = s[: -len(tok)].strip()
                changed = True
                break
    return s.replace(" ", "")


def bucket(candidate, enwiki_title):
    """exact / macron-only / mismatch / rejected for one gradeable item."""
    if candidate is None:
        return "rejected"
    c, e = core(candidate), core(enwiki_title)
    if c == e:
        return "exact"
    if c.translate(_MACRONS) == e.translate(_MACRONS):
        return "macron-only"
    return "mismatch"


def candidate_for(row):
    """The label the pipeline would produce for this row: hardcoded override, else normalize."""
    forced = hardcoded_label(row.get("ja", ""))
    if forced:
        return forced
    return commons_normalize.normalize(row.get("commons", ""))


def _romaji(name):
    """A Commons name this romaji stage even applies to — has an ASCII letter."""
    return any("a" <= c.lower() <= "z" for c in name)


def build_report(rows):
    """Grade every row. Rows: {qid, commons, enwiki, ja, en}. enwiki '' = not gradeable."""
    counts = {"in_scope": len(rows), "gradeable": 0, "non_romaji": 0}
    buckets = {"exact": 0, "macron-only": 0, "mismatch": 0, "rejected": 0}
    mismatches, rejected = [], []
    for r in rows:
        # A kanji Commons name ("厳島神社") is out of this romaji stage's scope — the kana
        # stage upstream handles those. Not a failure; excluded from the graded set.
        if not _romaji(r.get("commons", "")):
            counts["non_romaji"] += 1
            continue
        cand = candidate_for(r)
        if not r.get("enwiki"):
            continue                        # no ground truth — not gradeable
        counts["gradeable"] += 1
        b = bucket(cand, r["enwiki"])
        buckets[b] += 1
        if b == "mismatch":
            mismatches.append({"qid": r["qid"], "commons": r["commons"],
                               "candidate": cand, "enwiki": r["enwiki"]})
        elif b == "rejected":
            rejected.append({"qid": r["qid"], "commons": r["commons"], "enwiki": r["enwiki"]})
    g = counts["gradeable"]
    accuracy = (buckets["exact"] + buckets["macron-only"]) / g if g else 0.0
    return {"counts": counts, "buckets": buckets, "accuracy": accuracy,
            "mismatches": mismatches, "rejected": rejected}


# ─────────────────────────── live fetch ───────────────────────────

def sparql_csv(query):
    req = urllib.request.Request(
        SPARQL + "?" + urllib.parse.urlencode({"query": query}),
        headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def _query(p31_clause):
    # Commons category from the commonswiki sitelink; enwiki title where present.
    return """
SELECT ?item ?commons ?enwiki ?ja ?en WHERE {
  %s
  ?ccat schema:about ?item ; schema:isPartOf <https://commons.wikimedia.org/> ;
        schema:name ?commons .
  OPTIONAL { ?epage schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ;
             schema:name ?enwiki . }
  OPTIONAL { ?item rdfs:label ?ja  FILTER(lang(?ja)="ja") }
  OPTIONAL { ?item rdfs:label ?en  FILTER(lang(?en)="en") }
}""" % p31_clause


def fetch(limit=None):
    clauses = ["?item wdt:P31 wd:%s ." % SHRINE,
               "?item wdt:P31 wd:%s ; wdt:P17 wd:%s ." % (TEMPLE, JAPAN)]
    seen, rows = set(), []
    for clause in clauses:
        for r in sparql_csv(_query(clause)):
            qid = r["item"].rsplit("/", 1)[-1]
            if qid in seen:
                continue
            seen.add(qid)
            rows.append({"qid": qid,
                         "commons": (r.get("commons") or "").strip(),
                         "enwiki": (r.get("enwiki") or "").strip(),
                         "ja": (r.get("ja") or "").strip(),
                         "en": (r.get("en") or "").strip()})
            if limit and len(rows) >= limit:
                return rows
    return rows


# ─────────────────────────── output ───────────────────────────

def render_markdown(report, date_str):
    c, b = report["counts"], report["buckets"]
    out = ["# Commons → English-label accuracy (%s)\n" % date_str,
           "**Report only.** Grades `commons_normalize` against enwiki titles for Japanese "
           "shrines + temples. No edits proposed. "
           "Regenerate: `modern-quickstatements/report_commons_label_accuracy.py`.\n",
           "| | |\n|---|---:|",
           "| in-scope items (Commons category) | %d |" % c["in_scope"],
           "| non-romaji Commons name (out of scope — kana stage handles) | %d |"
           % c.get("non_romaji", 0),
           "| gradeable (romaji Commons name + enwiki title) | %d |" % c["gradeable"],
           "| **exact** | %d |" % b["exact"],
           "| **macron-only** (acceptable) | %d |" % b["macron-only"],
           "| **mismatch** (real failure) | %d |" % b["mismatch"],
           "| **rejected** (normalizer returned nothing) | %d |" % b["rejected"],
           "",
           "**Core-reading accuracy = %.1f%%** (exact + macron-only, over gradeable).\n"
           % (100 * report["accuracy"]),
           "## Mismatches — the real failures\n",
           "| item | Commons | candidate | enwiki |",
           "|---|---|---|---|"]
    for m in report["mismatches"]:
        out.append("| [%s](https://www.wikidata.org/wiki/%s) | %s | %s | %s |"
                   % (m["qid"], m["qid"], m["commons"], m["candidate"], m["enwiki"]))
    out.append("\n## Rejected — gradeable items the normalizer declined\n")
    out.append("| item | Commons | enwiki |\n|---|---|---|")
    for r in report["rejected"]:
        out.append("| [%s](https://www.wikidata.org/wiki/%s) | %s | %s |"
                   % (r["qid"], r["qid"], r["commons"], r["enwiki"]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--date", default="2026-07", help="date stamp for the filenames")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = fetch(args.limit)
    report = build_report(rows)

    md = os.path.join(DOC, "commons_label_accuracy_%s.md" % args.date)
    io.open(md, "w", encoding="utf-8", newline="\n").write(
        render_markdown(report, args.date))
    dump = os.path.join(HERE, "commons_label_mismatches.json")
    json.dump({"mismatches": report["mismatches"], "rejected": report["rejected"]},
              io.open(dump, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    b = report["buckets"]
    print("in-scope %d | gradeable %d | exact %d · macron-only %d · mismatch %d · rejected %d"
          % (report["counts"]["in_scope"], report["counts"]["gradeable"],
             b["exact"], b["macron-only"], b["mismatch"], b["rejected"]))
    print("core-reading accuracy %.1f%%" % (100 * report["accuracy"]))
    print("-> %s" % md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
