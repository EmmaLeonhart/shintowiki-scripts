"""
Shinto PROPERTY-name translation. The property-coverage report
(bfs/property_label_report.md) found most of the 806 properties are irrelevant
external-ID props; the genuinely Shinto-conceptual ones worth naming are few.
This translates them into the covered languages I'm confident about (hand-authored,
non-destructive). QuickStatements labels a property the same way: `P13723|Lde|"…"`.

Output: quickstatements/property_translations.txt
"""

import os
import sys
import io
import time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "quickstatements", "property_translations.txt")
SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "ShintoWikiPropTranslate/1.0 (immanuelleleonhart@gmail.com)",
      "Accept": "application/sparql-results+json"}

TRANSLATIONS = {
    "P13723": {  # shrine ranking (社格) — the rank a shrine holds
        "de": "Schreinrang", "nl": "schrijnrang", "sv": "helgedomsrang",
        "da": "helligdomsrang", "es": "rango del santuario", "ca": "rang del santuari",
        "gl": "rango do santuario", "pt": "categoria do santuário",
        "fr": "rang du sanctuaire", "it": "rango del santuario",
        "ro": "rangul altarului", "ru": "ранг святилища", "uk": "ранг святилища",
        "pl": "ranga chramu", "cs": "hodnost svatyně",
    },
    "P14005": {  # Japanese court rank (位階)
        "de": "japanischer Hofrang", "nl": "Japanse hofrang", "sv": "japansk hovrang",
        "da": "japansk hofrang", "es": "rango de la corte japonesa",
        "ca": "rang de la cort japonesa", "gl": "rango da corte xaponesa",
        "pt": "escalão da corte japonesa", "fr": "rang de cour japonais",
        "it": "rango di corte giapponese", "ro": "rang la curtea japoneză",
        "ru": "японский придворный ранг", "uk": "японський придворний ранг",
        "pl": "japońska ranga dworska", "cs": "japonská dvorská hodnost",
    },
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def existing_langs(pids):
    values = " ".join(f"wd:{p}" for p in pids)
    q = (f"SELECT ?item ?lang WHERE {{ VALUES ?item {{ {values} }} "
         f"?item rdfs:label ?l . BIND(LANG(?l) AS ?lang) }}")
    for a in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": q, "format": "json"}, headers=UA, timeout=90)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            r.raise_for_status()
            out = {}
            for b in r.json()["results"]["bindings"]:
                out.setdefault(b["item"]["value"].rsplit("/", 1)[1], set()).add(b["lang"]["value"])
            return out
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [retry {a+1}] {e}", flush=True)
            time.sleep(5 * (a + 1))
    raise RuntimeError("WDQS failed")


def main():
    _utf8()
    have = existing_langs(list(TRANSLATIONS))
    lines = []
    for pid, trans in TRANSLATIONS.items():
        for lang, label in trans.items():
            if lang not in have.get(pid, set()):          # non-destructive
                esc = label.replace('"', '""')
                lines.append(f'{pid}\tL{lang}\t"{esc}"')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"Wrote {len(lines)} property-name labels for {len(TRANSLATIONS)} props -> {OUT}")
    for ln in lines:
        print(" ", ln)


if __name__ == "__main__":
    main()
