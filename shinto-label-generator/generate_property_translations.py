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
# Split endpoint: query.wikidata.org is 429-outaged (2026-07-06+); query-main
# serves everything except scholarly articles, which is all we need.
SPARQL = "https://query-main.wikidata.org/sparql"
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
    # The 2026-07-06 reisai (P837) + bunrei (P612) imports use these properties
    # and qualifiers on every statement; their labels are the statement's UI in
    # each language (Emma 2026-07-07). zh-variant fills below are copies of the
    # property's own existing zh-hans/zh-hant forms, not new translations.
    "P612": {  # mother house — the 総本社 head each bunrei edge points at
        "pt": "casa-mãe", "gl": "casa nai", "ro": "casă-mamă",
        "hr": "matična kuća", "sh": "matična kuća", "el": "μητρικός οίκος",
        "ast": "casa madre",
    },
    "P837": {  # day in year for periodic occurrence — the reisai property
        "hr": "dan u godini",                       # existing sh label
        "zh-mo": "節日日期", "zh-sg": "节日日期",     # existing zh-hant / zh-hans
    },
    "P1013": {  # criterion used — bunrei qualifier (=Q195793)
        "sh": "korišteni kriterij",                 # existing hr label
        "zh-cn": "采用标准", "zh-sg": "采用标准",     # existing zh-hans
        "zh-tw": "採用標準", "zh-mo": "採用標準",     # existing zh-hant/zh-hk
    },
    "P3831": {  # object of statement has role — reisai qualifier (=Q11385469)
        "sh": "uloga objekta",                      # existing hr label
        "zh-cn": "客体的角色", "zh-sg": "客体的角色",  # existing zh-hans
        "zh-tw": "客體的角色", "zh-mo": "客體的角色",  # existing zh-hant/zh-hk
    },
    "P793": {  # significant event — Emma's 2026-07-07 standard: a shrine whose
        # annual festival has its OWN item points at it via P793 (cf. Q55522291).
        # Only 15 covered langs missing, all outside the confident set — nothing
        # authorable yet; entry kept so future gaps land here.
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
