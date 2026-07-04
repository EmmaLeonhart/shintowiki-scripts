"""
Property-label coverage report (queue item 3, bounded first step).

Enumerates the Wikidata properties used on the Shinto-CORE items (BFS levels 0-1
— the ranks / Engishiki / list concepts, where the meaningful Shinto properties
live) UNION the roadmap-named properties, then reports, per property, how many of
the covered languages (language_registry.COVERED) lack a label.

This is REPORT-ONLY reconnaissance — it does NOT emit any labels. Property labels
are TRANSLATION, not transliteration (per queue item 3), so the actual filling is
a separate, Emma-scoped step. Output: property_label_report.md + .json.

Load: one WDQS SPARQL query (a different service from the crawl's API) + a couple
of label API calls. Safe to run alongside the crawl.
"""

import os
import re
import sys
import io
import json
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from language_registry import COVERED  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS = os.path.join(HERE, "levels")
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": "ShintoWikiBFS-props/1.0 (immanuelleleonhart@gmail.com)",
      "Accept": "application/sparql-results+json"}

# Properties the roadmap (docs/mass-label-expansion-plan.md) + the Engishiki
# deprecation work explicitly care about — always included even if the core
# sample doesn't surface them (they live on shrine items in the drift layers).
ROADMAP_PROPS = ["P13723", "P14005", "P527", "P31", "P361", "P1343", "P1448",
                 "P1814", "P17", "P625"]


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(query):
    for attempt in range(4):
        time.sleep(0.4)
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
            print(f"  [retry {attempt+1}/4] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed")


def _get(params):
    for attempt in range(4):
        time.sleep(0.3)
        try:
            r = requests.get(API, params=params, headers=UA, timeout=60)
            if r.status_code == 429:
                raise SystemExit("HTTP 429 from Wikidata API — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {attempt+1}/4] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("API failed")


def read_core_qids():
    qids = []
    for lvl in ("level_00.tsv", "level_01.tsv"):
        p = os.path.join(LEVELS, lvl)
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                q = line.split("\t", 1)[0].strip()
                if re.match(r"^Q\d+$", q):
                    qids.append(q)
    return qids


def enumerate_properties(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    rows = _sparql(f"""SELECT DISTINCT ?p WHERE {{
      VALUES ?item {{ {values} }}
      ?item ?p ?v .
      FILTER(STRSTARTS(STR(?p), "http://www.wikidata.org/prop/direct/"))
    }}""")
    props = set()
    for b in rows:
        pid = b["p"]["value"].rsplit("/", 1)[1]
        if re.match(r"^P\d+$", pid):
            props.add(pid)
    return props


def fetch_property_labels(pids):
    out = {}
    pids = list(pids)
    for i in range(0, len(pids), 50):
        batch = pids[i:i + 50]
        data = _get({"action": "wbgetentities", "ids": "|".join(batch),
                     "props": "labels", "format": "json"})
        for p in batch:
            out[p] = data.get("entities", {}).get(p, {}).get("labels", {})
    return out


def main():
    _utf8()
    covered = sorted(COVERED)
    core = read_core_qids()
    print(f"Enumerating properties over {len(core)} Shinto-core items (levels 0-1)...")
    props = enumerate_properties(core) | set(ROADMAP_PROPS)
    print(f"  {len(props)} distinct properties (incl. {len(ROADMAP_PROPS)} roadmap props).")
    labels = fetch_property_labels(props)

    report = []
    for pid in props:
        L = labels.get(pid, {})
        en = L.get("en", {}).get("value", "")
        missing = [lg for lg in covered if lg not in L]
        report.append({"property": pid, "en": en,
                       "missing_count": len(missing), "missing": missing})
    report.sort(key=lambda r: (-r["missing_count"], r["property"]))

    with open(os.path.join(HERE, "property_label_report.json"), "w", encoding="utf-8") as f:
        json.dump({"covered_langs": len(covered), "properties": report}, f,
                  ensure_ascii=False, indent=2)

    fully = [r for r in report if r["missing_count"] == 0]
    lines = [
        "# Property-label coverage (queue item 3, bounded first step)",
        "",
        f"Properties used on the Shinto-core items (BFS levels 0-1) + roadmap props, "
        f"vs the {len(covered)} covered languages. REPORT ONLY — no labels emitted; "
        f"property labels are translation (Emma-scoped), not transliteration.",
        "",
        f"- Distinct properties examined: **{len(report)}**",
        f"- Fully covered in all {len(covered)} covered langs: **{len(fully)}**",
        f"- Missing in ≥1 covered lang: **{len(report) - len(fully)}**",
        "",
        "| Property | en label | # covered langs missing |",
        "|---|---|---:|",
    ]
    for r in report:
        lines.append(f"| {r['property']} | {r['en'] or '—'} | {r['missing_count']} |")
    with open(os.path.join(HERE, "property_label_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nWrote property_label_report.md ({len(report)} props; "
          f"{len(report)-len(fully)} have gaps).")
    for r in report[:12]:
        print(f"  {r['property']:8s} miss {r['missing_count']:2d}  {r['en']}")


if __name__ == "__main__":
    main()
