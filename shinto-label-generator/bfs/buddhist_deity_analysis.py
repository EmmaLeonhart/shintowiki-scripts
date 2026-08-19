"""
Analysis of the Buddhist deities (class Q65122124) — WHY the bare-name engine is
wrong for them and WHAT each one actually needs.

For each deity: existing label coverage across the covered languages, and its
labels in a few probe languages, so we can classify:
  - JP-NAMED  : English label reads as romanized Japanese (Fudō Myōō) -> the
                kami engine is safe for the gaps.
  - INTL/SANSKRIT : English label is NOT romaji (Indra, Avalokiteśvara) -> the
                engine gives the JP reading ("indora"), wrong; needs the
                established per-language name (mostly already on Wikidata).
  - WELL-COVERED : already has labels in most covered langs -> little/nothing to do.

Read-only. Output: buddhist_deity_analysis.md
"""

import os
import re
import sys
import io
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from language_registry import COVERED           # noqa: E402
from translit_common import looks_romaji         # noqa: E402
from shinto_miraheze.ua_contact import contact

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": WIKIDATA_USER_AGENT,
      "Accept": "application/sparql-results+json"}
CLASS = "Q65122124"
PROBES = ["en", "de", "fr", "es", "ru", "hi", "zh", "ko"]


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _get(url, params, post=False):
    for a in range(4):
        time.sleep(0.3)
        try:
            r = (requests.post if post else requests.get)(
                url, **({"data": params} if post else {"params": params}), headers=UA, timeout=90)
            if r.status_code == 429:
                raise SystemExit("429 — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {a+1}] {e}", flush=True)
            time.sleep(5 * (a + 1))
    raise RuntimeError("request failed")


def main():
    _utf8()
    covered = set(COVERED)
    rows = _get(SPARQL, {"query": f"SELECT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{CLASS} . }}",
                         "format": "json"}, post=True)["results"]["bindings"]
    qids = [b["item"]["value"].rsplit("/", 1)[1] for b in rows]
    print(f"{len(qids)} Buddhist deities. Fetching all labels...")

    ents = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        data = _get(API, {"action": "wbgetentities", "ids": "|".join(batch),
                          "props": "labels", "format": "json"})
        ents.update(data["entities"])

    analyzed = []
    for q in qids:
        L = ents.get(q, {}).get("labels", {})
        en = L.get("en", {}).get("value", "")
        ja = L.get("ja", {}).get("value", "")
        cov = sum(1 for lg in covered if lg in L)
        probes = {p: L.get(p, {}).get("value", "") for p in PROBES}
        # classify
        if cov >= 40:
            kind = "WELL-COVERED"
        elif en and looks_romaji(en):
            kind = "JP-NAMED"
        elif en:
            kind = "INTL/SANSKRIT"
        else:
            kind = "NO-EN"
        analyzed.append({"qid": q, "en": en, "ja": ja, "cov": cov, "kind": kind, "probes": probes})

    from collections import Counter
    kinds = Counter(a["kind"] for a in analyzed)

    lines = ["# Buddhist deities — analysis", "",
             f"{len(analyzed)} deities (class {CLASS}) vs the {len(covered)} covered languages.",
             "", "## Classification", "", "| Kind | Count | Meaning |", "|---|--:|---|",
             f"| WELL-COVERED (≥40 covered langs) | {kinds['WELL-COVERED']} | already labelled; leave alone |",
             f"| JP-NAMED (en is romaji) | {kinds['JP-NAMED']} | kami engine SAFE for gaps |",
             f"| INTL/SANSKRIT (en not romaji) | {kinds['INTL/SANSKRIT']} | engine WRONG; needs established name |",
             f"| NO-EN | {kinds['NO-EN']} | needs manual look |",
             "", "## Per-deity (sorted: problem set first)", "",
             "| qid | en | ja | cov | kind | de | fr | ru | hi |", "|---|---|---|--:|---|---|---|---|---|"]
    order = {"INTL/SANSKRIT": 0, "NO-EN": 1, "JP-NAMED": 2, "WELL-COVERED": 3}
    for a in sorted(analyzed, key=lambda x: (order[x["kind"]], -x["cov"])):
        p = a["probes"]
        lines.append(f"| {a['qid']} | {a['en']} | {a['ja']} | {a['cov']} | {a['kind']} | "
                     f"{p['de']} | {p['fr']} | {p['ru']} | {p['hi']} |")
    with open(os.path.join(HERE, "buddhist_deity_analysis.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n{dict(kinds)}")
    print("-> buddhist_deity_analysis.md")


if __name__ == "__main__":
    main()
