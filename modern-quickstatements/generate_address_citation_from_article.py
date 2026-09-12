"""
generate_address_citation_from_article.py
=========================================
Cite an existing, unreferenced `P6375` street address to the subject's OWN jawiki
article, where that article states the same address.

GENERATOR ONLY — writes QuickStatements lines into an atomic .txt file that the
single daily submitter runs. It never edits Wikidata and the lines carry no edit
summaries (CLAUDE.md "Wikidata editing — ONE path only").

## Why

Emma, 2026-09-11, on generators that create statements but never enrich the ones
already there: *"the updating of the existing ones to add more to them is kind of
a very critical part that makes it so that this work is productive."* Measured
that day: **4,777 shrine and 2,477 temple `P6375` statements carry no reference
at all.**

`generate_address_citation_backfill.py` already does this job, but only for
addresses it can match to a row of a 式内社一覧 per-district table — 139 lines.
Everything else is out of its reach, because the list article is the only source
it knows.

This one uses a different source that is available for almost every item: the
shrine's or temple's own jawiki article, whose `{{神社}}` / `{{日本の寺院}}`
infobox carries a `所在地` field.

## The gate is a value match, and it is the whole safety

A reference is emitted **only where the article's 所在地 normalises to exactly the
address the statement already holds.** That is what makes the citation true: we
are not asserting where the address came from, we are asserting that this article
says it. A statement whose value the article does not state is left alone —
it came from somewhere else, or the article has since changed, and citing it here
would assert something the article does not say.

Nothing is re-stated and no value is altered. `direct_daily_edits.execute_line`
matches the existing claim by value and attaches the reference group to it.

## Not in conflict with the removal pass

`generate_uncited_address_removals.py` deletes an uncited Japanese address only
on items that ALSO carry a cited one — Emma's rule, the citation being the signal
for which address is true. That population is disjoint from this one by
construction: an item it acts on already has a cited address, and an item whose
addresses are all uncited it deliberately leaves alone. Where both could touch
the same item the removal is the one that matters, and it is remove-only, so the
order the drip runs them in cannot lose an address.

Output: address_citation_from_article.txt
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
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import FIELD_TAIL

JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "address_citation_from_article.txt")
JA_WIKIPEDIA = "Q177837"

# Same two infoboxes the souken import reads, same FIELD_TAIL so a `|` inside a
# wikilink is not treated as a parameter boundary.
FIELD_RES = [re.compile(r"\|\s*所在地\s*=\s*" + FIELD_TAIL)]

TARGET_QUERY = """
SELECT ?item ?addr ?art WHERE {
  { ?item wdt:P31 wd:Q845945 } UNION { ?item wdt:P31 wd:Q5393308 }
  ?item p:P6375 ?st . ?st ps:P6375 ?addr .
  FILTER(LANG(?addr) = "ja")
  FILTER NOT EXISTS { ?st prov:wasDerivedFrom ?r }
  ?art schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> .
}
"""

# Characters that differ freely between a wikitext field and a stored value
# without changing the address: spaces of both widths, the postal mark and its
# digits, and the wiki markup around place names.
_POSTAL = re.compile(r"〒?\s*\d{3}[-−ー－]?\d{4}")
_SPACE = re.compile(r"[\s　]+")


def normalise(value):
    """An address reduced to what actually identifies it.

    Wiki markup, <ref>s, comments, a postal code and every kind of whitespace are
    dropped; a wikilink keeps its DISPLAY text, since `[[島根県|島根県]]` and
    `島根県` are the same address written two ways. Full-width digits are folded
    to ASCII because the two sources disagree about them freely.
    """
    v = value or ""
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<ref[^>]*/\s*>", "", v, flags=re.I)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.S | re.I)
    v = re.sub(r"<br\s*/?>", "", v, flags=re.I)
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    # [[target|display]] -> display; [[target]] -> target
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]", r"\1", v)
    v = v.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    v = _POSTAL.sub("", v)
    v = _SPACE.sub("", v)
    return v.strip(" 　-−ー－,、")


def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def sparql(query):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
        return json.load(r)["results"]["bindings"]


def targets():
    """{title: [(qid, address)]} — unreferenced ja addresses, by jawiki title.

    Keyed by title because the article is what gets fetched, and several items
    can share one (a 論社 pair documented in the same article)."""
    out = collections.defaultdict(list)
    for b in sparql(TARGET_QUERY):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        title = urllib.parse.unquote(
            b["art"]["value"].rsplit("/", 1)[-1]).replace("_", " ")
        out[title].append((qid, b["addr"]["value"]))
    return out


def article_addresses(titles):
    """{title: 所在地 field value} for a batch of articles."""
    d = _get({"action": "query", "prop": "revisions", "rvprop": "content",
              "rvslots": "main", "titles": "|".join(titles), "redirects": 1})
    out = {}
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        try:
            text = p["revisions"][0]["slots"]["main"]["*"]
        except (KeyError, IndexError):
            continue
        for pat in FIELD_RES:
            m = pat.search(text or "")
            if m:
                out[p["title"]] = m.group(1)
                break
    return out


def build_lines(by_title, field_by_title):
    """(lines, verdicts). One reference-only line per statement whose value the
    article still states."""
    lines, verdicts = [], collections.Counter()
    for title, entries in sorted(by_title.items()):
        field = field_by_title.get(title)
        if field is None:
            verdicts["article has no 所在地 field"] += len(entries)
            continue
        stated = normalise(field)
        if not stated:
            verdicts["所在地 field is empty once normalised"] += len(entries)
            continue
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(
            title.replace(" ", "_"))
        for qid, addr in sorted(entries):
            if normalise(addr) != stated:
                verdicts["article states a different address"] += 1
                continue
            esc = addr.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{qid}|P6375|ja:"{esc}"|S143|{JA_WIKIPEDIA}|S4656|"{url}"')
            verdicts["CITE"] += 1
    return lines, verdicts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUTPUT)
    ap.add_argument("--stats", action="store_true", help="report only, write nothing")
    ap.add_argument("--limit", type=int, help="only this many articles (sampling)")
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("=== Cite existing unreferenced P6375 addresses to their own article ===\n")
    by_title = targets()
    n = sum(len(v) for v in by_title.values())
    print(f"{n} unreferenced ja addresses across {len(by_title)} articles")

    titles = sorted(by_title)
    if args.limit:
        titles = titles[:args.limit]
        by_title = {t: by_title[t] for t in titles}
    field_by_title = {}
    for i in range(0, len(titles), 50):
        field_by_title.update(article_addresses(titles[i:i + 50]))
        time.sleep(0.3)
        if (i // 50) % 10 == 0:
            print(f"  fetched {min(i + 50, len(titles))}/{len(titles)} articles",
                  flush=True)

    lines, verdicts = build_lines(by_title, field_by_title)
    for verdict, count in verdicts.most_common():
        print(f"  {count:>6}  {verdict}")

    if args.stats:
        print(f"\n--stats: {len(lines)} lines would be written")
        return
    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    print(f"\nWrote {len(lines)} lines to {path}")


if __name__ == "__main__":
    main()
