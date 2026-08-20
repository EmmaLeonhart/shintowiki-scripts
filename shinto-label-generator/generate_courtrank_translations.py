"""
Court ranks (位階) — non-CJK lexical TRANSLATION (Emma: translate directly from the
English "Senior/Junior Nth Rank" into each language). The CJK/ko forms are already
in courtrank_labels.txt; this fills the alphabetic languages.

Rendered as "{rank-word} {N}, {senior|junior} grade" — using the digit avoids
per-language ordinal declension, and "senior/junior grade" is the accurate sense of
正 (senior) / 従 (junior). Only languages I'm confident about; others skipped.

Source: values of P14005 (Japanese court rank). Non-destructive via WDQS.
Output: quickstatements/courtrank_translations.txt
"""

import os
import re
import sys
import io
import time
import requests
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "quickstatements", "courtrank_translations.txt")
SPARQL = "https://query-main.wikidata.org/sparql"
UA = {"User-Agent": WIKIDATA_USER_AGENT,
      "Accept": "application/sparql-results+json"}

ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
           "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9}

# (template with {n} and {g}, senior word, junior word)
LANGS = {
    "de": ("Hofrang {n}, {g} Stufe", "obere", "untere"),
    "nl": ("hofrang {n}, {g} graad", "hogere", "lagere"),
    "sv": ("hovrang {n}, {g} grad", "högre", "lägre"),
    "da": ("hofrang {n}, {g} grad", "højere", "lavere"),
    "es": ("rango {n}, grado {g}", "superior", "inferior"),
    "ca": ("rang {n}, grau {g}", "superior", "inferior"),
    "gl": ("rango {n}, grao {g}", "superior", "inferior"),
    "pt": ("escalão {n}, grau {g}", "superior", "inferior"),
    "fr": ("rang {n}, {g}", "supérieur", "inférieur"),
    "it": ("rango {n}, grado {g}", "superiore", "inferiore"),
    "ro": ("rang {n}, grad {g}", "superior", "inferior"),
    "ru": ("{n}-й ранг, {g} разряд", "старший", "младший"),
    "uk": ("{n}-й ранг, {g} розряд", "старший", "молодший"),
    "pl": ("ranga {n}, stopień {g}", "wyższy", "niższy"),
    "cs": ("hodnost {n}, {g} stupeň", "vyšší", "nižší"),
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(q):
    for a in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": q, "format": "json"}, headers=UA, timeout=90)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {a+1}] {e}", flush=True)
            time.sleep(5 * (a + 1))
    raise RuntimeError("WDQS failed")


def main():
    _utf8()
    # court rank items + their en labels + existing languages, all via WDQS
    rows = _sparql("""SELECT ?item ?en (GROUP_CONCAT(DISTINCT ?lg;separator=",") AS ?langs) WHERE {
      ?x wdt:P14005 ?item .
      OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
      OPTIONAL { ?item rdfs:label ?l . BIND(LANG(?l) AS ?lg) }
    } GROUP BY ?item ?en""")

    lines, done = [], []
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[1]
        en = b.get("en", {}).get("value", "")
        have = set(b.get("langs", {}).get("value", "").split(","))
        m = re.match(r"^(Senior|Junior)\s+(\w+)\s+Rank$", en, re.I)
        if not m:
            continue
        grade, ordw = m.group(1).lower(), m.group(2).lower()
        n = ORDINAL.get(ordw)
        if not n:
            continue
        done.append(f"{qid} {en}")
        for lang, (tmpl, senior, junior) in LANGS.items():
            if lang in have:
                continue                       # non-destructive
            g = senior if grade == "senior" else junior
            label = tmpl.format(n=n, g=g)
            lines.append((qid, lang, label))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for qid, lang, label in lines:
            esc = label.replace('"', '""')
            f.write(f'{qid}\tL{lang}\t"{esc}"\n')
    print(f"Translated {len(done)} court ranks -> {len(lines)} labels "
          f"({len(LANGS)} langs) -> {OUT}")
    for d in done:
        print(f"  {d}")
    if lines:
        print("sample:", lines[0], "|", lines[1] if len(lines) > 1 else "")


if __name__ == "__main__":
    main()
