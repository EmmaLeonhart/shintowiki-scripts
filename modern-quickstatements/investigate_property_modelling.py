#!/usr/bin/env python3
"""
investigate_property_modelling.py
=================================
Statistical survey of how a property is MODELLED on a class of items — the
qualifiers it carries, the rate at which it is referenced, and which reference
properties/sources are used. The point is to discover the *established*
convention before extending a property (or adding a new one), rather than
inventing a model. Emma 2026-07-10: "do a statistical investigation of some of
the qualifiers and references on the deity property of the shrines, to find the
common qualifier modelling so that we can extend it … to other properties on
shrines and Buddhist temples."

READ-ONLY (SPARQL, query-main). 429 bails immediately (repo policy).

    python investigate_property_modelling.py                       # shrine+temple × P825
    python investigate_property_modelling.py --class Q5393308 --property P571
    python investigate_property_modelling.py --json

Output per (class, property): statement/item totals, qualifier distribution
(% of statements), reference rate, reference-property distribution, and the top
`stated in` (P248) sources — each with resolved English/Japanese labels.
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WDQS = "https://query-main.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"
DEFAULT_CLASSES = [("Q845945", "Shinto shrine"), ("Q5393308", "Buddhist temple")]


def _wdqs(query):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit("429 from WDQS — bailing (repo policy: no retries).")
        raise


def _labels(ids):
    ids = [i for i in dict.fromkeys(ids) if i]
    out = {}
    for i in range(0, len(ids), 50):
        u = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
            "props": "labels", "languages": "en|ja", "format": "json"})
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as r:
            ent = json.load(r)["entities"]
        for k, v in ent.items():
            labs = v.get("labels", {})
            out[k] = (labs.get("en", {}) or labs.get("ja", {})).get("value", "")
        time.sleep(0.2)
    return out


def _count_by(query, key):
    """{id: count}, summed in Python (query-main can emit duplicate binding rows)."""
    agg = {}
    for b in _wdqs(query):
        agg[b[key]["value"].rsplit("/", 1)[-1]] = agg.get(b[key]["value"].rsplit("/", 1)[-1], 0) \
            + int(b["n"]["value"])
    return agg


def investigate(cls, prop):
    tot = _wdqs(f"SELECT (COUNT(?st) AS ?n)(COUNT(DISTINCT ?s) AS ?items) "
                f"WHERE {{ ?s wdt:P31 wd:{cls}; p:{prop} ?st. }}")[0]
    total, items = int(tot["n"]["value"]), int(tot["items"]["value"])
    result = {"class": cls, "property": prop, "statements": total, "items": items,
              "qualifiers": {}, "referenced": 0, "ref_properties": {}, "sources": {}}
    if total == 0:
        return result
    time.sleep(1)
    result["qualifiers"] = _count_by(
        f"""SELECT ?k (COUNT(DISTINCT ?st) AS ?n) WHERE {{
          ?s wdt:P31 wd:{cls}; p:{prop} ?st. ?st ?k ?v.
          FILTER(STRSTARTS(STR(?k),"http://www.wikidata.org/prop/qualifier/")) }}
          GROUP BY ?k ORDER BY DESC(?n)""", "k")
    time.sleep(1)
    result["referenced"] = int(_wdqs(
        f"SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE {{ ?s wdt:P31 wd:{cls}; p:{prop} ?st. "
        f"?st prov:wasDerivedFrom ?ref. }}")[0]["n"]["value"])
    time.sleep(1)
    result["ref_properties"] = _count_by(
        f"""SELECT ?k (COUNT(DISTINCT ?st) AS ?n) WHERE {{
          ?s wdt:P31 wd:{cls}; p:{prop} ?st. ?st prov:wasDerivedFrom ?ref. ?ref ?k ?v.
          FILTER(STRSTARTS(STR(?k),"http://www.wikidata.org/prop/reference/")) }}
          GROUP BY ?k ORDER BY DESC(?n)""", "k")
    time.sleep(1)
    result["sources"] = _count_by(
        f"""SELECT ?k (COUNT(DISTINCT ?st) AS ?n) WHERE {{
          ?s wdt:P31 wd:{cls}; p:{prop} ?st. ?st prov:wasDerivedFrom ?ref. ?ref pr:P248 ?k. }}
          GROUP BY ?k ORDER BY DESC(?n) LIMIT 15""", "k")
    return result


def _print(result, labels):
    total = result["statements"]
    pct = lambda n: f"{100 * n / total:5.1f}%" if total else "  -  "
    def line(pid, n):
        return f"     {pid:8s} {n:6d}  {pct(n)}  {labels.get(pid, '')}"
    print(f"\n===== {labels.get(result['class'], result['class'])} — {result['property']} "
          f"({labels.get(result['property'], '')}) =====")
    print(f"  {total} statements over {result['items']} items; "
          f"{result['referenced']} referenced ({pct(result['referenced']).strip()})")
    print("  -- qualifiers (share of statements) --")
    for pid, n in sorted(result["qualifiers"].items(), key=lambda x: -x[1]) or [("(none)", 0)]:
        print(line(pid, n) if pid != "(none)" else "     (none)")
    print("  -- reference properties --")
    for pid, n in sorted(result["ref_properties"].items(), key=lambda x: -x[1]) or [("(none)", 0)]:
        print(line(pid, n) if pid != "(none)" else "     (none)")
    print("  -- top 'stated in' (P248) sources --")
    for pid, n in sorted(result["sources"].items(), key=lambda x: -x[1]) or [("(none)", 0)]:
        print(line(pid, n) if pid != "(none)" else "     (none)")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", help="class QID (default: shrine + temple)")
    ap.add_argument("--property", default="P825")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    classes = [(args.cls, args.cls)] if args.cls else DEFAULT_CLASSES

    results = [investigate(cls, args.property) for cls, _ in classes]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    ids = set()
    for r in results:
        ids.update([r["class"], r["property"]])
        ids.update(r["qualifiers"]); ids.update(r["ref_properties"]); ids.update(r["sources"])
    labels = _labels(list(ids))
    for r in results:
        _print(r, labels)


if __name__ == "__main__":
    main()
