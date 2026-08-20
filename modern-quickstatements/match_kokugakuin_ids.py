#!/usr/bin/env python3
"""
match_kokugakuin_ids.py
========================
One-shot matcher: assign P13677 (Kokugakuin University Digital Museum entry ID)
to the residual shikinaisha whose engishiki/ritsuryō P13723 statements are
unsourced *because* they lack the ID (the reference generator's
`skipped_no_p13677` set — 18 items as of 2026-07-08, down from 94).

Mechanics (probed 2026-07-08): entry detail pages carry the shrine name in the
static <title> ("［ID:181165］ 麻績神社"); the id space is ordered by 国/郡, so
each target's scan range is the min..max of KNOWN ids in its district ± margin
(district blocks span ~10-60 ids). Do NOT enumerate the whole 29,949..183,385
range. Polite ~1s throttle; harvested titles cached in
`kokugakuin_title_index.json` (committed — the index is reusable data).

Matching is STRICT, per Emma's 2026-07-08 ruling on the duplicate-ID work
(loose name-matching is prohibited in this territory):
  * exact string equality between the item's ja label and the entry title;
  * the id must not already be assigned to ANY item (never mint duplicates);
  * exactly ONE candidate id may match, and no other target in the same
    district may share the label (two 野蚊神社 in 河北郡 → both ambiguous);
  * anything else → kokugakuin_id_report.txt for per-item RAG, not guessed.

Output: kokugakuin_id_matches.txt — `Qxxx|P13677|"id"` (atomic, add-only).
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact

from shinto_miraheze.ua_for import ua_for

HERE = os.path.dirname(os.path.abspath(__file__))
WDQS = "https://query-main.wikidata.org/sparql"
# UA removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: UA = f"shintowiki-scripts/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id={}"
INDEX = os.path.join(HERE, "kokugakuin_title_index.json")
OUTPUT = os.path.join(HERE, "kokugakuin_id_matches.txt")
REPORT = os.path.join(HERE, "kokugakuin_id_report.txt")
MARGIN = 12
THROTTLE = 1.0

RANK_VALUES = ("Q134917287", "Q134917288", "Q9610964",
               "Q135160342", "Q135160338", "Q135009152")
_TITLE_RE = re.compile(r"<title>\s*([^<]*?)\s*</title>", re.S)
# cache stores the raw <title>; the entry NAME is the segment before the
# fullwidth-colon separator: "同社坐韓国伊太弖神社 ： 資料情報 | …"
_NAME_SEP = re.compile(r"\s*：\s*")
_DISTRICT_SUFFIX = ("郡", "国", "島")


def sparql(query):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": ua_for(url), "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        return json.load(r)["results"]["bindings"]


def fetch_targets():
    values = " ".join(f"wd:{v}" for v in RANK_VALUES)
    q = f"""SELECT DISTINCT ?item ?ja ?prov WHERE {{
      VALUES ?rankvalue {{ {values} }}
      ?item p:P13723 ?stmt . ?stmt ps:P13723 ?rankvalue .
      FILTER NOT EXISTS {{ ?stmt prov:wasDerivedFrom ?ref }}
      FILTER NOT EXISTS {{ ?item wdt:P13677 ?id }}
      OPTIONAL {{ ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }}
      OPTIONAL {{ ?item wdt:P131 ?m . ?m rdfs:label ?prov . FILTER(LANG(?prov)="ja") }}
    }}"""
    out = {}
    for b in sparql(q):
        g = lambda k: b.get(k, {}).get("value")
        d = out.setdefault(g("item").rsplit("/", 1)[-1], {"ja": None, "prov": set()})
        if g("ja"):
            d["ja"] = g("ja")
        if g("prov"):
            d["prov"].add(g("prov"))
    return out


def fetch_known():
    """[(id:int, prov:set)] for every assigned P13677, + the set of taken ids."""
    q = """SELECT ?item ?id ?prov WHERE {
      ?item wdt:P13677 ?id .
      OPTIONAL { ?item wdt:P131 ?m . ?m rdfs:label ?prov . FILTER(LANG(?prov)="ja") }
    }"""
    rows = {}
    for b in sparql(q):
        g = lambda k: b.get(k, {}).get("value")
        if not g("id").isdigit():
            continue
        d = rows.setdefault((g("item").rsplit("/", 1)[-1], int(g("id"))), set())
        if g("prov"):
            d.add(g("prov"))
    taken = {i for (_, i) in rows}
    return rows, taken


def harvest(ids, index):
    for i in sorted(ids):
        key = str(i)
        if key in index:
            continue
        req = urllib.request.Request(DET.format(i), headers={"User-Agent": ua_for(DET.format(i))})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read(4096).decode("utf-8", "replace")
            m = _TITLE_RE.search(html)
            index[key] = m.group(1).strip() if m else None
        except Exception as e:
            print(f"  id {i}: fetch failed ({e}) — leaving uncached")
        time.sleep(THROTTLE)
        if len(index) % 25 == 0:
            json.dump(index, open(INDEX, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=0)
    json.dump(index, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    targets = fetch_targets()
    print(f"{len(targets)} no-ID targets")
    time.sleep(1)
    known, taken = fetch_known()
    print(f"{len(known)} known (item,id) pairs")

    index = {}
    if os.path.exists(INDEX):
        index = json.load(open(INDEX, encoding="utf-8"))

    # district -> known-id block
    by_district = {}
    for (_, i), provs in known.items():
        for p in provs:
            if p.endswith(_DISTRICT_SUFFIX):
                by_district.setdefault(p, []).append(i)

    # scan ranges per target (union over its districts)
    scan = {}          # qid -> set(ids)
    unresolved = []    # no usable district anchor
    for qid, d in targets.items():
        dists = [p for p in d["prov"] if p.endswith(_DISTRICT_SUFFIX) and p in by_district]
        ids = set()
        for p in dists:
            block = by_district[p]
            ids.update(range(min(block) - MARGIN, max(block) + MARGIN + 1))
        if ids:
            scan[qid] = ids
        else:
            unresolved.append(qid)

    union = set().union(*scan.values()) if scan else set()
    todo = {i for i in union if str(i) not in index}
    print(f"scan union {len(union)} ids ({len(todo)} to harvest, "
          f"{len(unresolved)} targets with no district anchor)")
    harvest(todo, index)

    # entry-name -> ids, from the harvested index (unassigned ids only)
    lines, report = [], []
    # label collisions among targets sharing a district
    label_count = {}
    for qid, d in targets.items():
        for p in d["prov"]:
            label_count[(d["ja"], p)] = label_count.get((d["ja"], p), 0) + 1

    for qid, d in sorted(targets.items()):
        ja = d["ja"]
        if qid in unresolved or not ja:
            report.append(f"{qid} | {ja} | {'/'.join(sorted(d['prov']))} | NO-ANCHOR")
            continue
        if any(label_count[(ja, p)] > 1 for p in d["prov"]):
            report.append(f"{qid} | {ja} | {'/'.join(sorted(d['prov']))} | "
                          f"AMBIGUOUS: another target shares this label+district")
            continue
        def entry_name(i):
            t = index.get(str(i))
            return _NAME_SEP.split(t)[0] if t else None
        named = [i for i in sorted(scan[qid]) if entry_name(i) == ja]
        cands = [i for i in named if i not in taken]
        if len(cands) == 1:
            lines.append(f'{qid}|P13677|"{cands[0]}"')
        elif named:
            # every matching entry id is already assigned — the target is
            # probably a surplus/duplicate item, not an unmatched shrine.
            # Never mint a duplicate id; hand the holders to per-item review.
            detail = "; ".join(
                f"id {i} held by {','.join(sorted(h for (h, j) in known if j == i))}"
                for i in named)
            report.append(f"{qid} | {ja} | {'/'.join(sorted(d['prov']))} | "
                          f"ENTRY-TAKEN ({detail})")
        elif not cands:
            report.append(f"{qid} | {ja} | {'/'.join(sorted(d['prov']))} | NO-MATCH in scanned range")
        else:
            report.append(f"{qid} | {ja} | {'/'.join(sorted(d['prov']))} | "
                          f"AMBIGUOUS: ids {cands}")

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(report) + ("\n" if report else ""))
    print(f"{len(lines)} matches -> {OUTPUT}")
    print(f"{len(report)} for per-item review -> {REPORT}")
    for r in report:
        print("  " + r)


if __name__ == "__main__":
    main()
