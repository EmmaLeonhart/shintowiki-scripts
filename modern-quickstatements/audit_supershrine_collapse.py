"""How far does the piped-link collapse go? Three measurements, nothing staged.

Emma described the shape on `[[Open questions]]`, about 御笏神社 (`Q110915859`): the jawiki article
the import came from had several sessha written as piped links to the same shrine, so one Wikidata
item absorbed several register entries. The damage that leaves is visible in three places on that
one item, and nothing in the repo looks for any of them:

  1. ONE `P361` statement carrying FIVE `P1545` ordinals at once (5, 14, 16, 20, 34), with five
     `P155` and five `P156` piled into the same statement. A `part of` statement means one position
     in one list; more than one ordinal on it is the collapse, made literal.
  2. FIVE `P1814` readings, of which one is the shrine's (おしゃくじんじゃ) and four are ENTRY
     readings truncated with a hyphen — サキタマヒメノ-, ハヤシノ-, カタスカノ-, カミノ-. `Q135040908`
     carried `-カラクニイタテノ`, hyphen on the front instead. Same defect, both ends.
  3. ミナミコノ — the reading of 南子神社, one of the entries — stamped as a `P1814` qualifier on
     FIVE DIFFERENT `P1448` official names on that item.

⚠ The hyphen test must not catch **ー** (U+30FC, the katakana prolonged sound mark), which is
ordinary and correct in kana: シンジュクー would be a real reading. Only genuine hyphens count —
U+002D, U+2010, U+FF0D. Getting this wrong would report most of the kana corpus as broken.

MEASURES ONLY. It stages nothing and writes no QuickStatements, because the question is whether
these shapes are systemic or local to one item, and that is not something to guess at before
deciding what to do. Three aggregate SPARQL queries against `query-main`, grouped server-side so
only the offenders come back — not the batched sweep `CLAUDE.md` bans. Bails on 429.

Usage:
    python modern-quickstatements/audit_supershrine_collapse.py
    python modern-quickstatements/audit_supershrine_collapse.py --json supershrine_collapse.json
"""
import argparse
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

# One `part of` statement carrying more than one series ordinal.
MULTI_ORDINAL = """
SELECT ?item ?st (COUNT(DISTINCT ?ord) AS ?n) WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?item p:P361 ?st .
  ?st pq:P1545 ?ord .
}
GROUP BY ?item ?st
HAVING (COUNT(DISTINCT ?ord) > 1)
"""

# Readings truncated with a real hyphen at either end. U+30FC is deliberately NOT in the set.
HYPHEN_KANA = """
SELECT ?item ?kana WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?item wdt:P1814 ?kana .
  FILTER( STRSTARTS(?kana, "-") || STRENDS(?kana, "-")
       || STRSTARTS(?kana, "\\u2010") || STRENDS(?kana, "\\u2010")
       || STRSTARTS(?kana, "\\uFF0D") || STRENDS(?kana, "\\uFF0D") )
}
"""

# The same kana qualifier stamped on several different official names of one item.
SHARED_NAME_KANA = """
SELECT ?item ?kana (COUNT(DISTINCT ?name) AS ?n) WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?item p:P1448 ?st .
  ?st ps:P1448 ?name .
  ?st pq:P1814 ?kana .
}
GROUP BY ?item ?kana
HAVING (COUNT(DISTINCT ?name) > 1)
"""


def run(query):
    """One query, 429 bails, 503/504 backs off hard — the repo's standing WDQS policy.

    Every query here is scoped to `wdt:P31 wd:Q845945`. Unscoped, the first one asks the
    endpoint to group every `part of` statement on Wikidata and it returns 504.
    """
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"})
    for wait in (0, 15, 45, 135):
        if wait:
            print("  backing off %ds" % wait)
            time.sleep(wait)
        time.sleep(WDQS_THROTTLE)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("HTTP 429 from WDQS — bailing immediately per standing policy.")
                sys.exit(1)
            if exc.code in (503, 504):
                print("  HTTP %d from WDQS" % exc.code)
                continue
            raise
    print("WDQS kept timing out. Nothing measured — reporting that rather than a partial number.")
    sys.exit(1)


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    report = {}

    rows = run(MULTI_ORDINAL)
    items = {}
    for r in rows:
        items.setdefault(qid(r["item"]["value"]), []).append(int(r["n"]["value"]))
    worst = sorted(items.items(), key=lambda kv: -max(kv[1]))[:12]
    print("1. `part of` statements carrying MORE THAN ONE ordinal")
    print("   statements: %d   across items: %d" % (len(rows), len(items)))
    for item, counts in worst:
        print("     %-14s %s" % (item, ", ".join("%d ordinals in one statement" % c for c in counts)))
    report["multi_ordinal"] = {"statements": len(rows), "items": len(items),
                               "worst": [{"item": i, "counts": c} for i, c in worst]}

    rows = run(HYPHEN_KANA)
    lead = [r for r in rows if r["kana"]["value"][0] in "-‐－"]
    trail = [r for r in rows if r["kana"]["value"][-1] in "-‐－"]
    print("\n2. `name in kana` values truncated with a real hyphen (U+30FC excluded)")
    print("   total: %d   leading: %d   trailing: %d" % (len(rows), len(lead), len(trail)))
    for r in rows[:12]:
        print("     %-14s %s" % (qid(r["item"]["value"]), r["kana"]["value"]))
    report["hyphen_kana"] = {"total": len(rows), "leading": len(lead), "trailing": len(trail),
                             "sample": [{"item": qid(r["item"]["value"]),
                                         "kana": r["kana"]["value"]} for r in rows[:60]]}

    rows = run(SHARED_NAME_KANA)
    print("\n3. one kana qualifier stamped on SEVERAL different official names of one item")
    print("   (item, kana) groups: %d" % len(rows))
    for r in rows[:12]:
        print("     %-14s %s  on %s different names"
              % (qid(r["item"]["value"]), r["kana"]["value"], r["n"]["value"]))
    report["shared_name_kana"] = {"groups": len(rows),
                                  "sample": [{"item": qid(r["item"]["value"]),
                                              "kana": r["kana"]["value"],
                                              "names": int(r["n"]["value"])} for r in rows[:60]]}

    if args.json_out:
        path = args.json_out if os.path.isabs(args.json_out) else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), args.json_out)
        io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=2))
        print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
