#!/usr/bin/env python3
"""Property + PROPERTY->QUALIFIER census for kami and Shinto shrines. Live.

Emma 2026-07-16:
  "you did have some sort of statistical report on properties and qualifiers of
   kami and Shinto shrines... I want to know what's actually going on with it."
  on the old report: "it's only looking at qualifiers on the deity property,
   which makes it almost useless!"
  on a flat qualifier list: "a qualifier is utterly contextually useless outside
   of the property that it qualifies."

So this reports PROPERTY -> QUALIFIER pairs, not a flat qualifier list, and does
it for instances of kami and of Shinto shrine.

docs/deity_qualifier_analysis_2026-07.md counted qualifiers on P825 only —
"we can just say it didn't happen".

Read-only. Run: python report_ontology_state.py
"""
import io
import json
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UA = "shintowiki-scripts/1.0 (https://emmaleonhart.com; ontology census)"
SPARQL = "https://query.wikidata.org/sparql"

KAMI = "wd:Q524158"
SHRINE = "wd:Q845945"


def run(q, timeout=300):
    url = SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["results"]["bindings"]


def count(q):
    return int(run(q)[0]["c"]["value"])


def props(cls, label, n):
    """Every direct property on the class. No label service — it is what 504s."""
    print(f"\n{'='*74}\n{label} — {n:,} items — PROPERTIES\n{'='*74}")
    rows = run(f"""
    SELECT ?p (COUNT(DISTINCT ?i) AS ?c) WHERE {{
      ?i wdt:P31/wdt:P279* {cls} .
      ?i ?prop ?v .
      ?p wikibase:directClaim ?prop .
    }} GROUP BY ?p ORDER BY DESC(?c)""")
    out = [(r["p"]["value"].split("/")[-1], int(r["c"]["value"])) for r in rows]
    labels = pids_to_labels([p for p, _ in out])
    print(f"{'property':46} {'items':>8} {'cov':>7}")
    print("-" * 74)
    for pid, c in out:
        nm = f"{labels.get(pid, '')} ({pid})"
        print(f"{nm[:46]:46} {c:>8,} {c/n*100:>6.1f}%")
    return out


def prop_qualifiers(cls, label):
    """PROPERTY -> QUALIFIER pairs. The only framing that means anything."""
    print(f"\n{'='*74}\n{label} — QUALIFIERS, BY THE PROPERTY THEY QUALIFY\n{'='*74}")
    rows = run(f"""
    SELECT ?p ?q (COUNT(*) AS ?c) WHERE {{
      ?i wdt:P31/wdt:P279* {cls} .
      ?i ?pp ?st .
      ?p wikibase:claim ?pp .
      ?st ?pq ?qv .
      ?q wikibase:qualifier ?pq .
    }} GROUP BY ?p ?q ORDER BY DESC(?c)""")
    pairs = [(r["p"]["value"].split("/")[-1], r["q"]["value"].split("/")[-1],
              int(r["c"]["value"])) for r in rows]
    labels = pids_to_labels({p for p, _, _ in pairs} | {q for _, q, _ in pairs})

    by_prop = {}
    for p, q, c in pairs:
        by_prop.setdefault(p, []).append((q, c))
    order = sorted(by_prop, key=lambda p: -sum(c for _, c in by_prop[p]))
    for p in order:
        tot = sum(c for _, c in by_prop[p])
        print(f"\n{labels.get(p,'')} ({p})  — {tot:,} qualified statements")
        for q, c in sorted(by_prop[p], key=lambda t: -t[1]):
            print(f"    {(labels.get(q,'') + ' (' + q + ')')[:52]:52} {c:>7,}")
    return by_prop


_LBL = {}


def pids_to_labels(pids):
    """Fetch property labels via the API in batches — cheaper than the label service."""
    todo = [p for p in set(pids) if p not in _LBL]
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(chunk),
            "props": "labels", "languages": "en", "format": "json"}))
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
        for pid, e in d.get("entities", {}).items():
            _LBL[pid] = e.get("labels", {}).get("en", {}).get("value", "")
        time.sleep(0.3)
    return _LBL


def main():
    for cls, label in [(KAMI, "KAMI (Q524158)"), (SHRINE, "SHINTO SHRINE (Q845945)")]:
        try:
            n = count(f"SELECT (COUNT(DISTINCT ?i) AS ?c) WHERE {{ ?i wdt:P31/wdt:P279* {cls} . }}")
            props(cls, label, n)
            time.sleep(2)
            prop_qualifiers(cls, label)
            time.sleep(2)
        except Exception as exc:
            print(f"\n{label}: QUERY FAILED — {exc}")


if __name__ == "__main__":
    main()
