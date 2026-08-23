"""Find descriptions sitting on items that have NO label in that language.

Emma's ruling, 2026-08-21 -- the "extremely important caveat" of her four-step description
algorithm, and step 1 of it:

    "we always remove descriptions from items without a label in that language"

    "many items can have the same label and empty descriptions, and many items can have the
     same description and an empty label, but once the two of them are both filled then it
     rejects edits to one to avoid duplication. Since labels are overwhelmingly more
     important than descriptions, it follows that any description on an item without a label
     is actively harmful."

WHY IT IS HARMFUL, stated once so nobody re-derives it. Wikidata's uniqueness constraint is
on the **(label, description) pair** in a language; either field alone may repeat freely.
So a description on a label-less item is a claim staked on one half of a pair -- the half
that matters least. When the label finally arrives, the completed pair can collide with an
existing item, and it is the LABEL edit that gets rejected. A description with no label
costs a label.

That is why removal is step 1 and not step 4: it clears an obstruction to the thing that
actually matters.

This script only MEASURES and STAGES. It emits `Qxxx|D<lang>|""` lines, which is how
QuickStatements clears a description, into an atomic file for the normal daily drip. It
never edits Wikidata itself -- per `CLAUDE.md`, the QuickStatements pipeline is the single
road, and a bespoke direct-API editor is forbidden.

⛔ Nothing can be delivered before the Wikidata lockout lifts on 2026-09-18
(`shinto_miraheze/wikidata_editing_lockout.state`). Staging is workable; delivering is not.

Usage:
    python modern-quickstatements/audit_orphan_descriptions.py --count
    python modern-quickstatements/audit_orphan_descriptions.py --lang en --emit
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
SHRINE = "Q845945"

# The floor set by generate_genbu_ids.py after a rematch drew repeated 503/504. These are
# heavy aggregate queries; they get the same respect.
WDQS_THROTTLE = 2.5

OUT = os.path.join(HERE, "orphan_description_removals.txt")
REPORT = os.path.join(HERE, "orphan_descriptions_audit.json")

# One query, grouped by language, instead of one per language. The FILTER NOT EXISTS is the
# whole test: a description whose language has no matching label on the same item.
COUNT_QUERY = """
SELECT ?lang (COUNT(DISTINCT ?item) AS ?n) WHERE {
  ?item wdt:P31 wd:%s .
  ?item schema:description ?desc .
  BIND(LANG(?desc) AS ?lang)
  FILTER NOT EXISTS {
    ?item rdfs:label ?label .
    FILTER(LANG(?label) = LANG(?desc))
  }
}
GROUP BY ?lang
ORDER BY DESC(?n)
"""

# Every orphan (item, language) pair in ONE query. 100 per-language queries would be the
# shape `CLAUDE.md` names as the thing that drew repeated 503/504 and got the pacing rule
# written; this is one request for the same data.
ALL_QUERY = """
SELECT ?item ?lang WHERE {
  ?item wdt:P31 wd:%s .
  ?item schema:description ?desc .
  BIND(LANG(?desc) AS ?lang)
  FILTER NOT EXISTS {
    ?item rdfs:label ?label .
    FILTER(LANG(?label) = LANG(?desc))
  }
}
"""

LIST_QUERY = """
SELECT ?item ?desc WHERE {
  ?item wdt:P31 wd:%s .
  ?item schema:description ?desc .
  FILTER(LANG(?desc) = "%s")
  FILTER NOT EXISTS {
    ?item rdfs:label ?label .
    FILTER(LANG(?label) = "%s")
  }
}
"""


def sparql(query):
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as fh:
        data = json.load(fh)
    time.sleep(WDQS_THROTTLE)
    return data["results"]["bindings"]


def count_by_language():
    rows = sparql(COUNT_QUERY % SHRINE)
    return [(r["lang"]["value"], int(r["n"]["value"])) for r in rows]


def orphans_in(lang):
    rows = sparql(LIST_QUERY % (SHRINE, lang, lang))
    return [(r["item"]["value"].rsplit("/", 1)[-1], r["desc"]["value"]) for r in rows]


def removal_line(qid, lang):
    """QuickStatements clears a description by setting it to the empty string.

    Deliberately NOT a leading-dash removal: `-Qxxx|Den|"…"` is a value-matched remove and
    would need the exact current text. Setting empty is unconditional and cannot mismatch.
    """
    return '%s|D%s|""' % (qid, lang)


def main(argv=None):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", action="store_true",
                    help="count orphan descriptions per language (one query)")
    ap.add_argument("--lang", help="list/emit for a single language")
    ap.add_argument("--emit", action="store_true",
                    help="write removal QuickStatements for --lang into the atomic file")
    args = ap.parse_args(argv)

    if args.count or not args.lang:
        rows = count_by_language()
        total = sum(n for _, n in rows)
        print("descriptions with NO label in the same language, on P31=%s items" % SHRINE)
        print("  %-8s %s" % ("lang", "items"))
        for lang, n in rows:
            print("  %-8s %d" % (lang or "(none)", n))
        print("  %-8s %d across %d languages" % ("TOTAL", total, len(rows)))
        with io.open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"per_language": dict(rows), "total": total}, fh,
                      ensure_ascii=False, indent=2)
        print("wrote %s" % os.path.relpath(REPORT, ROOT))
        return 0

    rows = orphans_in(args.lang)
    print("%s: %d orphan descriptions" % (args.lang, len(rows)))
    for qid, desc in rows[:10]:
        print("   %-12s %s" % (qid, desc[:70]))
    if not args.emit:
        print("(--emit to stage removals)")
        return 0

    # Sorted, and merged with whatever is already staged, so a re-run is a no-op rather
    # than a duplicate append. The 2026-08-21 churn lesson applies to any generated file.
    existing = []
    if os.path.exists(OUT):
        existing = [l.strip() for l in io.open(OUT, encoding="utf-8") if l.strip()]
    merged = set(existing) | {removal_line(qid, args.lang) for qid, _ in rows}

    def key(line):
        qid, rest = line.split("|", 1)
        return (rest, int(qid[1:]) if qid[1:].isdigit() else 0, qid)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sorted(merged, key=key)) + "\n")
    print("%s: staged %d, file now holds %d removal lines (%d new) -> %s"
          % (args.lang, len(rows), len(merged), len(merged) - len(existing),
             os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
