"""Shrines that HAVE an English label but no name in kana — and what their name-mates read.

Emma, 2026-08-24, refining the English-label rule. An English label ends an item for the
purposes of *deriving* a reading from its article — but she is open to reviewing that population,
and named the method she wants if kana is ever added to it:

    "What it does is it takes the English-language label, compares it with other things that have
     the same English-language label and have a name in kana, finds the most common name in kana,
     and then applies that one to that shrine that doesn't have it."

    "My view is essentially that highly repeated names are going to be ones that don't carry
     errors."

    "Ideally, I'd like to look at very common kanji-English language label pairs and their name in
     kana… I just feel like the kanji plus the English language label is almost certainly going to
     be the case for very common names."

So the unit is the **(ja label, en label) PAIR**, not the English label alone — two shrines that
share both are far more likely to share a reading than two that merely share a romanisation.

⚠ **A different convention is not an error.** Her caveat, and it governs how conflicts are read:
Engishiki readings are ancient and follow different conventions from modern ones, so a pair whose
kana disagree is not evidence that either the English label or the reading is wrong. Conflicts are
for her to rule on, not for this to resolve.

REPORTS ONLY. It writes no QuickStatements and stages nothing. Its job is to say how big the
population is, how much of it is covered by a confident majority, and which pairs are common enough
to be worth a ruling — so the decision is made on numbers.

Usage:
    python modern-quickstatements/report_en_label_without_kana.py
    python modern-quickstatements/report_en_label_without_kana.py --json en_label_without_kana.json
"""
import argparse
import collections
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

ENDPOINT = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5

# Every shrine with an English label, with its ja label and its kana if it has one.
# One query; the split into has-kana / lacks-kana happens here, not on the endpoint.
SHRINES = """
SELECT ?item ?ja ?en ?kana WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?item rdfs:label ?en . FILTER(LANG(?en)="en")
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
  OPTIONAL { ?item wdt:P1814 ?kana }
}
"""


def run(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    for wait in (0, 15, 45, 135):
        if wait:
            print("  backing off %ds" % wait)
            time.sleep(wait)
        time.sleep(WDQS_THROTTLE)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("HTTP 429 from WDQS — bailing immediately per standing policy.")
                sys.exit(1)
            if exc.code in (503, 504):
                print("  HTTP %d from WDQS" % exc.code)
                continue
            raise
    print("WDQS kept timing out. Nothing measured.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--min-support", type=int, default=2,
                    help="how many name-mates must agree before a majority counts (default 2)")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    rows = run(SHRINES)
    print("shrines with an English label: %d rows" % len(rows))

    # (ja, en) -> {kana -> count}, and the items on that pair that have no kana at all
    votes = collections.defaultdict(collections.Counter)
    missing = collections.defaultdict(list)
    seen = set()
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        ja = b.get("ja", {}).get("value", "")
        en = b["en"]["value"]
        key = (ja, en)
        kana = b.get("kana", {}).get("value")
        if kana:
            votes[key][kana] += 1
        elif (qid, key) not in seen:
            missing[key].append(qid)
        seen.add((qid, key))

    total_missing = sum(len(v) for v in missing.values())
    print("distinct (ja, en) pairs: %d" % len(set(list(votes) + list(missing))))
    print("items with an English label and NO kana: %d" % total_missing)

    resolvable, unanimous, split, unsupported = [], 0, [], 0
    for key, qids in missing.items():
        counter = votes.get(key)
        if not counter:
            unsupported += len(qids)
            continue
        top, n = counter.most_common(1)[0]
        if n < args.min_support:
            unsupported += len(qids)
            continue
        entry = {"ja": key[0], "en": key[1], "kana": top, "support": n,
                 "distinct_readings": len(counter),
                 # the full vote, so a "disagreement" can be read as what it usually is:
                 # one dominant reading and a short tail of older conventions
                 "readings": counter.most_common(), "items": qids}
        resolvable.append(entry)
        if len(counter) == 1:
            unanimous += len(qids)
        else:
            split.append(entry)

    covered = sum(len(e["items"]) for e in resolvable)
    print("\n--- how far the name-mate majority reaches (min support %d) ---" % args.min_support)
    print("  items a majority could fill:      %d" % covered)
    print("      of those, name-mates UNANIMOUS: %d" % unanimous)
    print("      of those, readings DISAGREE:    %d" % (covered - unanimous))
    print("  items with no supported name-mate: %d" % unsupported)

    resolvable.sort(key=lambda e: -e["support"])
    print("\n--- most-supported pairs (the safe end: many name-mates, one reading) ---")
    for e in [x for x in resolvable if x["distinct_readings"] == 1][:15]:
        print("  %-3d %-22s %-34s %s" % (e["support"], e["ja"], e["en"], e["kana"]))

    split.sort(key=lambda e: -e["support"])
    print("\n--- pairs where name-mates DISAGREE (these need a ruling, not a majority) ---")
    for e in split[:12]:
        tail = "  ".join("%s×%d" % (k, v) for k, v in e["readings"][:5])
        print("  %-16s %-22s %s" % (e["ja"], e["en"], tail))

    if args.json_out:
        path = args.json_out if os.path.isabs(args.json_out) else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), args.json_out)
        io.open(path, "w", encoding="utf-8").write(json.dumps({
            "items_missing_kana": total_missing,
            "min_support": args.min_support,
            "covered_by_majority": covered,
            "unanimous": unanimous,
            "disagreeing": covered - unanimous,
            "no_supported_name_mate": unsupported,
            "pairs": resolvable,
        }, ensure_ascii=False, indent=2))
        print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
