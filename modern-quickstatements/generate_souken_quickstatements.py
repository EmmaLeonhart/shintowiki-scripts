#!/usr/bin/env python3
"""
generate_souken_quickstatements.py
===================================
Import founding dates from jawiki infoboxes onto Wikidata as P571 (inception)
— shrines ({{神社}} 創建) and temples ({{日本の寺院}} 創建年), from
`docs/jawiki_infobox_import_review_2026-07.md`.

CONSERVATIVE parser (verified against a live 50-article sample): the dominant
clean pattern is an era date with a parenthetical Gregorian year —
「[[貞観 (日本)|貞観]]5年（[[863年]]）」. Only fields that reduce to exactly ONE
unambiguous Gregorian year are imported, at year precision. Skipped by design
(counted, never force-parsed):

  * 伝 / （伝）  — legendary attributions (a future pass may import these with
    the P1480 "presumably" sourcing-circumstances qualifier; Emma's call);
  * 不詳 / 頃 / ? / BC / 年間 — unknown, circa, ranges, era-spans;
  * fields with MULTIPLE distinct years (per-building dates, "before X" notes);
  * fields with no Gregorian year at all (era-only or regnal-only, per jawiki
    citation-style rules some articles deliberately omit the Western year).

Items already carrying P571 are skipped for the IMPORT. Output: souken_p571.txt —
    <item>|P571|+YYYY-00-00T00:00:00Z/9|S143|Q177837|S4656|"<jawiki url>"

## The citation backfill (added 2026-09-11)

Skipping them entirely left their statements permanently unsourced: 441 shrine
and 1,030 temple P571 statements carry no reference at all, and this generator —
the only thing that reads 創建 — could never reach one. Emma, on generators that
create but never enrich: *"the updating of the existing ones to add more to them
is kind of a very critical part that makes it so that this work is productive."*

So an item that already has P571 now also gets checked: where its statement is
UNREFERENCED and jawiki still states the SAME year the statement holds, the same
reference bundle is emitted into souken_p571_citations.txt.

The year match is the whole safety of it. A statement whose year differs from
what the article now says came from somewhere else, or the article has changed;
citing it to this article would assert something the article does not say, so
those are counted as `year-mismatch` and skipped. Nothing is re-stated, no value
is altered — QuickStatements matches the existing claim by value and attaches the
reference to it.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import io
import json
import os
import re

import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import FIELD_TAIL, field_pattern

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT = os.path.join(HERE, "souken_p571.txt")
# The citation backfill: the SAME reference bundle onto P571 statements that
# already exist and carry no source. Separate file so it can be paced or stopped
# without touching the import (Emma, 2026-09-11).
CITE_OUTPUT = os.path.join(os.path.dirname(OUTPUT), "souken_p571_citations.txt")

# A field value ends at the next `|` parameter boundary, NOT at the newline.
# Articles that put the whole infobox on one line otherwise bleed the next
# parameter into the value. 本願寺西山別院 reads
#     |創建=平安時代|開基=|中興年=[[1314年|1314年（正和3年）]]|…
# and `([^\n]*)` swallowed all of it, importing the 中興 *restoration* year 1314 as
# the temple's founding date. Three such lines were withdrawn on 2026-07-10, and
# only because the bled text happened to contain a refused marker (中興); a bled
# parameter carrying a bare year would have leaked silently.
#
# A `|` inside [[wikilinks]] or {{templates}} is not a boundary — Japanese era
# links look like [[大同 (日本)|大同]]. This is exactly the pattern that
# generate_saijin_quickstatements and generate_honzon_quickstatements have always
# used; souken, kofun and p3225 were the three that did not.
_FIELD_TAIL = FIELD_TAIL   # shared; see infobox_fields.py

CONFIGS = [
    ("Template:神社", r"\|\s*創建\s*=\s*" + _FIELD_TAIL),
    ("Template:日本の寺院", r"\|\s*創建年\s*=\s*" + _FIELD_TAIL),
]
_YEAR_RE = re.compile(r"(\d{3,4})年")

# Vague: the article declines to give a definite year.
# 不明 was missing until 2026-07-09 — only 不詳 was listed — and 大御食神社's field is
# literally `不明` followed by a <ref> whose *citation* carries "1921年". Both gaps
# together produced a confident P571 of 1921 for a shrine whose founding jawiki calls
# unknown. Neither gap is theoretical.
_VAGUE = r"不詳|不明|未詳|頃|\?|？|紀元前|BC|年間|以前|以降|世紀"

# A rebuild/relocation year is not a founding year. 竹林寺 (生駒市) reads
# `伝・奈良時代初期<br />再興：平成9年（1997年）`: the only Gregorian year in the field
# belongs to the 再興, and the founding has none. Where such a marker is present this
# script cannot attribute the year, so it declines.
_REBUILD = r"再興|再建|中興|復興|移転|遷座|再造"

_SKIP_RE = re.compile(r"伝|" + _VAGUE + "|" + _REBUILD)

_CITE_TEMPLATES = {"sfn", "refnest", "efn", "reflist", "citation", "r"}


def _strip_matching_templates(text, names):
    """Remove balanced {{name|...}} templates, so nested braces don't cut short."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("{{", i):
            depth, j = 0, i
            while j < n:
                if text.startswith("{{", j):
                    depth += 1
                    j += 2
                elif text.startswith("}}", j):
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            if depth != 0:                       # unbalanced — leave it alone
                out.append(text[i])
                i += 1
                continue
            name = text[i + 2:j - 2].split("|", 1)[0].strip().lower()
            # Prefix matching, not just the literal set: `{{Sfnp}}` / `{{Sfnm}}` /
            # `{{Harvnb}}` are as much citations as `{{Sfn}}`, and 瀧泉寺's field
            # `泰叡山{{Sfnp|江戸名所図会|1927|p=101}}` shows they occur in the wild.
            # A missed citation template leaks its publication year into the value.
            if (name in names or name.startswith("cite")
                    or name.startswith("sfn") or name.startswith("harv")):
                i = j
                continue
            out.append(text[i:j])
            i = j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def strip_citations(field):
    """Drop comments, <ref>…</ref>, and citation templates.

    A citation's publication year is not the subject's founding year. Before this,
    only `{{sfn}}` was stripped — and only by a regex that stops at the first `}}`,
    so a nested `{{Refnest|…{{NDLDC|…}}…}}` survived and leaked its years.
    """
    field = re.sub(r"<!--.*?-->", "", field, flags=re.S)
    field = re.sub(r"<ref[^>]*/\s*>", "", field, flags=re.I)
    field = re.sub(r"<ref[^>]*>.*?</ref>", "", field, flags=re.S | re.I)
    return _strip_matching_templates(field, _CITE_TEMPLATES)


def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def embedded_titles(template):
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": template,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def parse_year(field):
    """The single unambiguous Gregorian year, or None."""
    field = strip_citations(field)
    if not field.strip() or _SKIP_RE.search(field):
        return None
    years = {int(y) for y in _YEAR_RE.findall(field)}
    years = {y for y in years if 300 <= y <= 2026}   # era-year "5年" noise is <300
    if len(years) != 1:
        return None
    return years.pop()


def _wdqs(q):
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        return json.load(r)["results"]["bindings"]


def items_with_p571():
    """(qids carrying P571, {qid: {year}} for the UNREFERENCED statements only).

    The second half is what the citation backfill needs. Emma, 2026-09-11, on
    generators that create but never enrich: *"the updating of the existing ones
    to add more to them is kind of a very critical part that makes it so that
    this work is productive."* Measured that day: 441 shrine and 1,030 temple
    inception statements carry no reference at all, and this generator could
    never reach them because it skips any item that already has P571.

    The year is carried, not just the QID, because a reference may only be
    attached where jawiki still states the SAME year the statement holds — see
    the backfill line in main().
    """
    rows = _wdqs("SELECT ?item WHERE { { ?item wdt:P31 wd:Q845945 } UNION "
                 "{ ?item wdt:P31 wd:Q5393308 } ?item wdt:P571 [] . }")
    have = {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}

    rows = _wdqs("""SELECT ?item ?v WHERE {
      { ?item wdt:P31 wd:Q845945 } UNION { ?item wdt:P31 wd:Q5393308 }
      ?item p:P571 ?st . ?st ps:P571 ?v .
      FILTER NOT EXISTS { ?st prov:wasDerivedFrom ?r }
    }""")
    uncited = {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        # "+0863-00-00T00:00:00Z" -> 863. A negative (BCE) year is not something
        # this generator ever parses, so it simply never matches.
        m = re.match(r"^\+(\d{4})-", b["v"]["value"])
        if m:
            uncited.setdefault(qid, set()).add(int(m.group(1)))
    return have, uncited


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have, uncited = items_with_p571()
    print(f"{len(have)} shrines/temples already carry P571; "
          f"{len(uncited)} of them have an UNREFERENCED P571 statement")
    lines, cite_lines = [], []
    for template, field_pat in CONFIGS:
        pat = re.compile(field_pat)
        titles = embedded_titles(template)
        if args.limit:
            titles = titles[:args.limit]
        clean = skipped = no_qid = already = cited = mismatch = 0
        for i in range(0, len(titles), 50):
            for title, qid, text in fetch_batch(titles[i:i + 50]):
                m = pat.search(text or "")
                if not m:
                    continue
                year = parse_year(m.group(1))
                if year is None:
                    skipped += 1
                    continue
                if not qid:
                    no_qid += 1
                    continue
                url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                if qid in have:
                    already += 1
                    # THE CITATION BACKFILL. The statement exists and carries no
                    # source; jawiki is where it came from, so jawiki can cite it
                    # — but ONLY where the article still states the same year the
                    # statement holds. A year mismatch means the statement came
                    # from somewhere else or jawiki has since changed, and citing
                    # it to this article would assert something the article does
                    # not say.
                    if year in uncited.get(qid, ()):
                        cite_lines.append(
                            f'{qid}|P571|+{year:04d}-00-00T00:00:00Z/9'
                            f'|S143|Q177837|S4656|"{url}"')
                        cited += 1
                    elif qid in uncited:
                        mismatch += 1
                    continue
                lines.append(f'{qid}|P571|+{year:04d}-00-00T00:00:00Z/9|S143|Q177837|S4656|"{url}"')
                clean += 1
            time.sleep(0.3)
        print(f"{template}: {len(titles)} articles, clean-year={clean}, "
              f"skipped-ambiguous={skipped}, no-QID={no_qid}, already-had-P571={already} "
              f"(citable={cited}, year-mismatch={mismatch})")
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P571 lines -> {OUTPUT}")

    cite_lines = sorted(set(cite_lines))
    with open(CITE_OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cite_lines) + ("\n" if cite_lines else ""))
    print(f"{len(cite_lines)} P571 citation-backfill lines -> {CITE_OUTPUT}")


if __name__ == "__main__":
    main()
