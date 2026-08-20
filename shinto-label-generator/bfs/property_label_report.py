"""
Property-label coverage report (queue item 3, bounded first step).

Enumerates the Wikidata properties used on the Shinto-CORE items (BFS levels 0-1
— the ranks / Engishiki / list concepts, where the meaningful Shinto properties
live) as MAIN statement values (wdt:), QUALIFIERS (pq:), AND references (pr:),
UNION the roadmap-named properties, then reports, per property, how many of the
covered languages (language_registry.COVERED) lack a label. Qualifiers are
included deliberately: Shinto properties are heavily qualified, so a large share
of the properties that need labels appear only as qualifiers.

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
from shinto_miraheze.ua_contact import contact

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS = os.path.join(HERE, "levels")
SPARQL = "https://query-main.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": WIKIDATA_USER_AGENT,
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


_PID_TAIL = re.compile(r"/(P\d+)$")


def enumerate_properties(qids):
    """Distinct P-ids used on the items as MAIN statement values (wdt:),
    QUALIFIERS (pq:), AND references (pr:) — a property needs a label wherever
    it appears, not just on truthy main statements."""
    values = " ".join(f"wd:{q}" for q in qids)
    rows = _sparql(f"""
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT DISTINCT ?p WHERE {{
      VALUES ?item {{ {values} }}
      {{
        ?item ?p ?v .
        FILTER(STRSTARTS(STR(?p), "http://www.wikidata.org/prop/direct/"))
      }} UNION {{
        ?item ?ps ?st .
        ?st ?p ?qv .
        FILTER(STRSTARTS(STR(?p), "http://www.wikidata.org/prop/qualifier/"))
      }} UNION {{
        ?item ?ps ?st .
        ?st prov:wasDerivedFrom ?ref .
        ?ref ?p ?rv .
        FILTER(STRSTARTS(STR(?p), "http://www.wikidata.org/prop/reference/"))
      }}
    }}""")
    props = set()
    for b in rows:
        m = _PID_TAIL.search(b["p"]["value"])
        if m:
            props.add(m.group(1))
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
        f"Properties used on the Shinto-core items (BFS levels 0-1) as MAIN values, "
        f"QUALIFIERS, and references, + roadmap props, vs the {len(covered)} covered "
        f"languages. Qualifiers matter — Shinto properties are heavily qualified. "
        f"REPORT ONLY — no labels emitted; property labels are translation "
        f"(Emma-scoped), not transliteration.",
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
