"""
report_stuck_katakana_readings.py
=================================
The top-level katakana `P1814` values the カミノヤシロ pipeline cannot reach, sorted
into categories for a per-category ruling.

REPORT ONLY — queries Wikidata and writes a Markdown file. No QuickStatements, no
edits.

## Why anything is stuck

`generate_kana_qualifier_remove.py` removes a top-level katakana reading only when
the item's ojp-hani `P1448` official name carries a qualifier that is **exactly**
that reading plus `カミノヤシロ`. That exactness is deliberate and load-bearing —
its own docstring records three 論社 whose entry carries a DIFFERENT entry's
reading, where a loose match would have deleted a reading that exists nowhere
else.

The other pipeline (`generate_katakana_reading_add.py` / `_remove.py`) explicitly
excludes any item carrying an ojp-hani `P1448`.

So an item with an ojp-hani name whose qualifier does not exactly match its
top-level katakana falls between the two and is reachable by neither. Emma hit one
on 2026-09-10, `Q11361262` 下立松原神社: top-level `シモタテ-`, name qualifier
`シモタチマツハラノ`, and a perfectly good modern hiragana already present.

## What the categories are for

Emma, 2026-09-11: *"give me a comprehensive list of the categories and I'll say
what to do with each individually."* So this groups the population on the three
things that decide whether a value can be touched at all:

  * **is the reading preserved elsewhere** — does the ojp-hani name carry a
    `カミノヤシロ`-suffixed qualifier (the pipeline's own confirmation), an
    unsuffixed one, or nothing;
  * **does the item have a modern hiragana reading** as well;
  * **the shape of the value** — a leading- or trailing-hyphen fragment, a
    space-separated pair, or a whole reading.

The hyphen is the signal that matters most: it marks where a longer reading was
cut off, so the value is a piece rather than a name.

Usage:
    python report_stuck_katakana_readings.py                 # write the report
    python report_stuck_katakana_readings.py --out docs/x.md
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

import argparse
import collections
import datetime
import io
import os
import sys
import time

import requests

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
SUFFIX = "カミノヤシロ"
DEFAULT_OUT = os.path.join("..", "docs", "stuck_katakana_readings.md")

QUERY = """
SELECT ?item ?ja ?top ?q ?hira ?on WHERE {
  ?item wdt:P31 wd:Q845945 ; p:P1814 ?ts .
  ?ts ps:P1814 ?top .
  ?item p:P1448 ?st . ?st ps:P1448 ?on . FILTER(LANG(?on) = "ojp-hani")
  OPTIONAL { ?st pq:P1814 ?q }
  OPTIONAL { ?item wdt:P1814 ?hira }
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja") }
}
"""


def sparql(query, retries=3):
    for attempt in range(1, retries + 1):
        time.sleep(2.5)
        try:
            r = requests.post(SPARQL_ENDPOINT, data={"query": query, "format": "json"},
                              headers={"User-Agent": UA,
                                       "Accept": "application/sparql-results+json"},
                              timeout=300)
        except requests.exceptions.ReadTimeout:
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            return None
        if r.status_code == 429:
            raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
        r.raise_for_status()
        try:
            return r.json()["results"]["bindings"]
        except ValueError:
            if attempt < retries:
                time.sleep(15 * attempt)
                continue
            return None
    return None


def is_katakana(value):
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def shape(value):
    """What the value LOOKS like, which is what says whether it is a name."""
    if " " in value or "　" in value:
        return "two readings in one value"
    if value.startswith("-") or value.startswith("‐") or value.startswith("−"):
        return "fragment, head cut off"
    if value.endswith("-") or value.endswith("‐") or value.endswith("−"):
        return "fragment, tail cut off"
    if "-" in value:
        return "fragment, middle cut out"
    return "whole reading"


def preservation(quals, top):
    """Where else this item's ancient reading lives, if anywhere."""
    if (top + SUFFIX) in quals:
        return "removable by the pipeline today"
    if any(q.endswith(SUFFIX) for q in quals):
        return "name carries a confirmed カミノヤシロ reading"
    if quals:
        return "name carries a reading, but unconfirmed (no カミノヤシロ)"
    return "name carries no reading at all"


def collect(rows):
    items = collections.defaultdict(
        lambda: {"ja": "", "on": "", "top": set(), "quals": set(), "all": set()})
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        rec = items[qid]
        rec["top"].add(b["top"]["value"])
        if "q" in b:
            rec["quals"].add(b["q"]["value"])
        if "hira" in b:
            rec["all"].add(b["hira"]["value"])
        if "ja" in b:
            rec["ja"] = b["ja"]["value"]
        if "on" in b:
            rec["on"] = b["on"]["value"]
    return items


def categorise(items):
    """{(preservation, has_hiragana, shape): [(qid, ja, top, quals)]}"""
    cats = collections.defaultdict(list)
    for qid, rec in items.items():
        has_hira = any(not is_katakana(v) for v in rec["all"])
        for top in sorted(v for v in rec["top"] if is_katakana(v)):
            key = (preservation(rec["quals"], top), has_hira, shape(top))
            cats[key].append((qid, rec["ja"], top, sorted(rec["quals"])))
    return cats


def render(cats, total):
    today = datetime.date.today().isoformat()
    out = [f"# Stuck katakana `P1814` readings — categories for a ruling, {today}",
           "",
           "Generated by `modern-quickstatements/report_stuck_katakana_readings.py`. "
           "Report only; nothing is staged.",
           "",
           "Emma, 2026-09-11: *\"give me a comprehensive list of the categories and "
           "I'll say what to do with each individually.\"*",
           "",
           "## Why these are stuck",
           "",
           "`generate_kana_qualifier_remove.py` removes a top-level katakana reading "
           "only when the item's ojp-hani `P1448` name carries a qualifier that is "
           "**exactly** that reading plus `カミノヤシロ`. That exactness is deliberate: "
           "its docstring records three 論社 whose entry carries a *different* entry's "
           "reading, where a loose match would delete a reading that exists nowhere "
           "else. The other pipeline "
           "(`generate_katakana_reading_add.py`) excludes any item with an ojp-hani "
           "`P1448` outright. An item whose qualifier does not exactly match its "
           "top-level value is reachable by neither.",
           "",
           f"**{total} top-level katakana statements** on shrines carrying an "
           "ojp-hani official name.",
           "",
           "## Summary",
           "",
           "| n | reading preserved? | item has hiragana? | shape |",
           "|---:|---|---|---|"]
    for key, rows in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        pres, hira, shp = key
        out.append(f"| {len(rows)} | {pres} | {'yes' if hira else 'no'} | {shp} |")
    out += ["", "## The categories in full", ""]
    for key, rows in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        pres, hira, shp = key
        out += [f"### {len(rows)} — {pres}; "
                f"hiragana {'present' if hira else 'absent'}; {shp}",
                ""]
        if pres == "removable by the pipeline today":
            out += ["Nothing to decide: the existing removal generator reaches "
                    "these. Listed for completeness.", ""]
        elif pres == "name carries no reading at all" and not hira:
            out += ["⛔ **This value is the item's ONLY reading.** Removing it "
                    "loses the reading entirely — there is no qualifier on the "
                    "official name and no modern hiragana.", ""]
        elif pres == "name carries a confirmed カミノヤシロ reading":
            out += ["The ancient reading provably survives on the official name, "
                    "so the top-level copy is redundant in the way the pipeline's "
                    "own removals are — it just does not match exactly.", ""]
        elif pres == "name carries a reading, but unconfirmed (no カミノヤシロ)":
            out += ["The official name carries *a* reading, but without the "
                    "`カミノヤシロ` suffix the pipeline has never confirmed it, so "
                    "whether it covers this value is a judgement call.", ""]
        elif not hira:
            out += ["No modern hiragana on the item either, so removing this "
                    "leaves the item with no reading at all.", ""]
        out += ["| item | ja label | top-level value | qualifiers on the ojp-hani name |",
                "|---|---|---|---|"]
        for qid, ja, top, quals in sorted(rows)[:25]:
            qs = ", ".join(f"`{q}`" for q in quals) if quals else "—"
            out.append(f"| [{qid}](https://www.wikidata.org/wiki/{qid}) | {ja} | "
                       f"`{top}` | {qs} |")
        if len(rows) > 25:
            out.append(f"| … | *{len(rows) - 25} more* | | |")
        out.append("")
    out += ["## Ruling", "",
            "One line per category, written here by Emma; the removal generator is "
            "then pointed at whichever categories she clears.", ""]
    for key, rows in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        pres, hira, shp = key
        out.append(f"* **{len(rows)}** — {pres}; hiragana "
                   f"{'present' if hira else 'absent'}; {shp} → ")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    print("Querying top-level katakana P1814 on shrines with an ojp-hani name...")
    rows = sparql(QUERY)
    if rows is None:
        print("No SPARQL result — leaving the existing report untouched.")
        return
    items = collect(rows)
    cats = categorise(items)
    total = sum(len(v) for v in cats.values())
    path = args.out if os.path.isabs(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(cats, total))
    print(f"{total} statements in {len(cats)} categories -> {path}")
    for key, rows_ in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(rows_):>5}  {key[0]}; hiragana={'yes' if key[1] else 'no'}; {key[2]}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
