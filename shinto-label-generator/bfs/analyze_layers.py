"""
Analyze each BFS layer (level_NN.tsv) by Wikidata type (P31), to see WHAT the
items are and which already have a labelling approach.

Already-covered (excluded from new labelling work, but NOT pruned from the graph):
  - Shinto shrines            — P31/P279* Q845945  (algorithmic shrine names)
  - Buddhist temples          — P31/P279* Q5393308 (algorithmic temple names)
  - Shikinaisha list articles — the generate_shikinaisha_list pipeline

Everything else is a candidate for a new labelling approach. This script prints,
per layer, the type distribution split into covered vs. to-do, and writes
layer_analysis.json for the write-up.

Read-only, chunked, throttled — safe to run alongside the crawl.
"""

import os
import re
import sys
import io
import json
import time
import glob
import requests
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS_DIR = os.path.join(HERE, "levels")
OUT_JSON = os.path.join(HERE, "layer_analysis.json")

SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "ShintoWikiBFS-analyze/1.0 ({contact('wikidata')})",
      "Accept": "application/sparql-results+json"}
CHUNK = 250
THROTTLE = 0.4

SHRINE_ROOT = "Q845945"     # Shinto shrine
TEMPLE_ROOT = "Q5393308"    # Buddhist temple
LIST_TYPES = {"Q13406463", "Q12139612", "Q1980247"}   # Wikimedia list article & kin


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def sparql(query):
    """POST with bounded retries on transient 5xx / network errors. 429 bails."""
    last = None
    for attempt in range(4):
        time.sleep(THROTTLE)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=UA, timeout=120)
            if r.status_code == 429:
                raise SystemExit("HTTP 429 from WDQS — bailing (repo policy).")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            last = e
            wait = 5 * (attempt + 1)
            print(f"  [retry {attempt+1}/4] WDQS {e}; waiting {wait}s...", flush=True)
            time.sleep(wait)
    raise last


def read_level(path):
    qids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            q = line.split("\t", 1)[0].strip()
            if re.match(r"^Q\d+$", q):
                qids.append(q)
    return qids


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_p31(qids):
    """qid -> set(type_qid). Items with no P31 map to empty set."""
    types = {q: set() for q in qids}
    for ch in chunks(qids, CHUNK):
        values = " ".join(f"wd:{q}" for q in ch)
        rows = sparql(f"SELECT ?item ?type WHERE {{ VALUES ?item {{ {values} }} "
                      f"?item wdt:P31 ?type. }}")
        for b in rows:
            q = b["item"]["value"].rsplit("/", 1)[1]
            t = b["type"]["value"].rsplit("/", 1)[1]
            types.setdefault(q, set()).add(t)
    return types


def classify_types(type_qids):
    """For the distinct type QIDs, return dicts: label, is_shrine, is_temple."""
    labels, shrine, temple = {}, set(), set()
    tq = sorted(type_qids)
    for ch in chunks(tq, CHUNK):
        values = " ".join(f"wd:{q}" for q in ch)
        rows = sparql(f"SELECT ?type ?typeLabel WHERE {{ VALUES ?type {{ {values} }} "
                      f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}')
        for b in rows:
            q = b["type"]["value"].rsplit("/", 1)[1]
            labels[q] = b.get("typeLabel", {}).get("value", q)
        # which of these types are subclass* of shrine / temple
        for root, bucket in ((SHRINE_ROOT, shrine), (TEMPLE_ROOT, temple)):
            rows = sparql(f"SELECT ?type WHERE {{ VALUES ?type {{ {values} }} "
                          f"?type wdt:P279* wd:{root}. }}")
            for b in rows:
                bucket.add(b["type"]["value"].rsplit("/", 1)[1])
    return labels, shrine, temple


def main():
    _utf8()
    level_files = sorted(glob.glob(os.path.join(LEVELS_DIR, "level_*.tsv")))
    print(f"Analyzing {len(level_files)} level files.\n")

    # Gather P31 for all items across all levels (dedup fetches).
    all_qids = []
    level_qids = {}
    for path in level_files:
        d = int(re.search(r"level_(\d+)", path).group(1))
        qs = read_level(path)
        level_qids[d] = qs
        all_qids.extend(qs)
    uniq = sorted(set(all_qids), key=lambda x: int(x[1:]))
    print(f"Fetching P31 for {len(uniq)} unique items across all layers...")
    types = fetch_p31(uniq)

    distinct_types = set()
    for s in types.values():
        distinct_types |= s
    print(f"Resolving {len(distinct_types)} distinct P31 classes...")
    labels, shrine_types, temple_types = classify_types(distinct_types)

    def bucket_of(item):
        ts = types.get(item, set())
        if ts & shrine_types:
            return "shrine"
        if ts & temple_types:
            return "temple"
        if ts & LIST_TYPES:
            return "list"
        return "todo"

    report = {}
    for d in sorted(level_qids):
        qs = level_qids[d]
        covered = {"shrine": 0, "temple": 0, "list": 0, "todo": 0}
        todo_class_counts = {}
        no_p31 = 0
        for q in qs:
            b = bucket_of(q)
            covered[b] += 1
            if b == "todo":
                ts = types.get(q, set())
                if not ts:
                    no_p31 += 1
                for t in ts:
                    todo_class_counts[t] = todo_class_counts.get(t, 0) + 1
        top = sorted(todo_class_counts.items(), key=lambda kv: -kv[1])[:25]
        report[d] = {
            "total": len(qs),
            "covered": covered,
            "no_p31_in_todo": no_p31,
            "top_todo_classes": [
                {"type": t, "label": labels.get(t, t), "count": c} for t, c in top
            ],
        }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Print human-readable
    for d in sorted(report):
        r = report[d]
        c = r["covered"]
        print(f"\n{'='*66}\nLAYER {d}: {r['total']} items")
        print(f"  already-covered: shrine={c['shrine']}  temple={c['temple']}  "
              f"list={c['list']}")
        print(f"  TO-DO (need a labelling approach): {c['todo']}"
              f"  (of which {r['no_p31_in_todo']} have no P31)")
        if r["top_todo_classes"]:
            print(f"  top to-do types:")
            for e in r["top_todo_classes"]:
                print(f"    {e['count']:5d}  {e['label']}  ({e['type']})")
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
