"""
Build the MISCELLANEOUS bucket: every linked thing in the BFS corpus that does
NOT cleanly fall into shrines / gods / geographic locations (nor the other
already-handled buckets: temples, shrine-ranks, provinces, Shikinaisha lists).

This is the thorny residual — texts, objects, rituals, offices, whatever. Output
is a single file (miscellaneous.tsv: qid, en, ja, P31 type labels) that is the
input to a later analysis. NO labelling/translation happens here — this only
lists and types the residual.

Source: the crawled corpus (levels 0-2, the Shinto core where the residual
concentrates; level 3 is ~46k of geographic drift). Read-only Wikidata (WDQS for
P31 + subclass, API for labels).
"""

import os
import re
import sys
import io
import time
import requests
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
CORE = ("level_00.tsv", "level_01.tsv", "level_02.tsv")
OUT = os.path.join(HERE, "miscellaneous.tsv")

SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": WIKIDATA_USER_AGENT,
      "Accept": "application/sparql-results+json"}
CHUNK = 250

# Types to REMOVE — only the clean buckets that are NOT the misc residual:
# shrines / temples / gods / geographic locations, plus the already-handled
# rank / province / list. Deliberately light — better to over-include and let
# the later analysis prune than to remove too much here.
EASY_ROOTS = {
    "Q845945":  "shrine",
    "Q5393308": "temple",
    "Q178885":  "deity",          # gods (incl. Buddhist deities)
    "Q524158":  "kami",
    "Q2221906": "geographic location",
    "Q56061":   "admin territorial entity",
    "Q6256":    "country",
    "Q515":     "city",
    "Q486972":  "human settlement",
    "Q860290":  "province of Japan",
    "Q10444029": "shrine rank",
    "Q13406463": "list article",
    "Q15221623": "bilateral relation",   # "X–Japan relations" — ignore per Emma
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(q):
    for a in range(4):
        time.sleep(0.4)
        try:
            r = requests.post(SPARQL, data={"query": q, "format": "json"}, headers=UA, timeout=120)
            if r.status_code == 429:
                raise SystemExit("HTTP 429 from WDQS — bailing.")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {a+1}/4] {e}", flush=True)
            time.sleep(5 * (a + 1))
    raise RuntimeError("WDQS failed")


def _api(params):
    for a in range(4):
        time.sleep(0.3)
        try:
            r = requests.get(API, params=params, headers=UA, timeout=60)
            if r.status_code == 429:
                raise SystemExit("HTTP 429 from API — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {a+1}/4] {e}", flush=True)
            time.sleep(5 * (a + 1))
    raise RuntimeError("API failed")


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def read_corpus():
    qids, seen = [], set()
    for name in CORE:
        p = os.path.join(LEVELS, name)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            q = line.split("\t", 1)[0].strip()
            if re.match(r"^Q\d+$", q) and q not in seen:
                seen.add(q)
                qids.append(q)
    return qids


def fetch_types(qids):
    """type(s) per item from BOTH P31 (instance of) AND P279 (subclass of), so
    concept-CLASSES (which carry P279 but often no P31) are not dropped."""
    types = {q: set() for q in qids}
    for ch in _chunks(qids, CHUNK):
        vals = " ".join(f"wd:{q}" for q in ch)
        for b in _sparql(f"SELECT ?item ?t WHERE {{ VALUES ?item {{ {vals} }} "
                         f"?item (wdt:P31|wdt:P279) ?t. }}"):
            types[b["item"]["value"].rsplit("/", 1)[1]].add(b["t"]["value"].rsplit("/", 1)[1])
    return types


def easy_typeset(distinct_types):
    """Distinct P31 types that are subclass* of any EASY root -> NOT miscellaneous."""
    easy = set()
    tq = sorted(distinct_types)
    roots = " ".join(f"wd:{r}" for r in EASY_ROOTS)
    for ch in _chunks(tq, CHUNK):
        vals = " ".join(f"wd:{t}" for t in ch)
        for b in _sparql(f"SELECT DISTINCT ?t WHERE {{ VALUES ?t {{ {vals} }} "
                         f"VALUES ?root {{ {roots} }} ?t wdt:P279* ?root. }}"):
            easy.add(b["t"]["value"].rsplit("/", 1)[1])
    return easy


def type_labels(type_qids):
    labels = {}
    for ch in _chunks(sorted(type_qids), CHUNK):
        vals = " ".join(f"wd:{t}" for t in ch)
        for b in _sparql(f'SELECT ?t ?tLabel WHERE {{ VALUES ?t {{ {vals} }} '
                         f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}'):
            labels[b["t"]["value"].rsplit("/", 1)[1]] = b.get("tLabel", {}).get("value", "")
    return labels


def item_labels(qids):
    out = {}
    for ch in _chunks(qids, 50):
        data = _api({"action": "wbgetentities", "ids": "|".join(ch),
                     "props": "labels", "languages": "en|ja", "format": "json"})
        for q in ch:
            L = data.get("entities", {}).get(q, {}).get("labels", {})
            out[q] = (L.get("en", {}).get("value", ""), L.get("ja", {}).get("value", ""))
    return out


def main():
    _utf8()
    qids = read_corpus()
    print(f"Corpus (levels 0-2): {len(qids)} items. Fetching P31 + P279...")
    types = fetch_types(qids)
    distinct = set().union(*types.values()) if types else set()
    print(f"  {len(distinct)} distinct P31 types. Resolving 'easy' (shrine/god/geo/…) subclasses...")
    easy = easy_typeset(distinct)

    misc = [q for q in qids if types[q] and not (types[q] & easy)]
    print(f"  {len(misc)} miscellaneous items (no P31 under an easy bucket).")

    tlabels = type_labels({t for q in misc for t in types[q]})
    ilabels = item_labels(misc)

    rows = []
    for q in misc:
        en, ja = ilabels.get(q, ("", ""))
        tnames = ", ".join(sorted(tlabels.get(t, t) for t in types[q]))
        rows.append((q, en, ja, tnames))
    rows.sort(key=lambda r: r[3])  # group by type

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("qid\ten\tja\tp31_types\n")
        for q, en, ja, tn in rows:
            f.write(f"{q}\t{en}\t{ja}\t{tn}\n")
    print(f"\nWrote {len(rows)} rows -> {OUT}")

    # composition summary
    from collections import Counter
    comp = Counter(r[3] for r in rows)
    print("\ntop type-signatures in the miscellaneous bucket:")
    for sig, n in comp.most_common(20):
        print(f"  {n:4d}  {sig[:70]}")


if __name__ == "__main__":
    main()
