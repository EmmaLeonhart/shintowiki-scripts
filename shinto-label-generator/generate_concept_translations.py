"""
TRANSLATION-tier run (daily ~15:00 cron): descriptive Shinto concepts translated
(not transliterated) into the covered languages. Hand-authored per the hard rail
— only items + languages I'm confident about; uncertain ones are omitted, never
invented. World religions (already labelled everywhere) and court ranks (the
established rendering of 正/従 varies by language) are deliberately deferred.

Non-destructive: existing labels fetched via SPARQL (WDQS) — a different service
from the rate-limited API — and only missing (item, lang) pairs are emitted.
State in concept_translations.state so successive runs don't repeat items.

Output: quickstatements/concept_translations.txt
"""

import os
import re
import sys
import io
import json
import time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "quickstatements", "concept_translations.txt")
STATE = os.path.join(HERE, "concept_translations.state")
SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "ShintoWikiConceptTranslate/1.0 (immanuelleleonhart@gmail.com)",
      "Accept": "application/sparql-results+json"}

# Hand-authored translations. Only languages I'm confident about per item; a
# language omitted for an item = "unclear, skip", not a gap to guess.
TRANSLATIONS = {
    "Q3395121": {  # wayside shrine (道端の祠)
        "de": "Wegschrein", "nl": "wegschrijn", "sv": "vägkantshelgedom",
        "es": "santuario junto al camino", "ca": "santuari a la vora del camí",
        "gl": "santuario á beira do camiño", "pt": "santuário à beira do caminho",
        "fr": "sanctuaire de bord de route", "it": "santuario lungo la strada",
        "ro": "altar de margine de drum", "ru": "придорожное святилище",
        "uk": "придорожне святилище", "pl": "przydrożna kapliczka",
        "cs": "přícestní svatyně",
    },
    "Q97361976": {  # fictional kami (架空の神)
        "de": "fiktive Gottheit", "nl": "fictieve godheid", "sv": "fiktiv gudom",
        "da": "fiktiv guddom", "es": "deidad ficticia", "ca": "deïtat fictícia",
        "gl": "deidade ficticia", "pt": "divindade fictícia",
        "fr": "divinité fictive", "it": "divinità immaginaria",
        "ro": "divinitate fictivă", "ru": "вымышленное божество",
        "uk": "вигадане божество", "pl": "fikcyjne bóstwo", "cs": "fiktivní božstvo",
    },
    "Q66890725": {  # Tenjin faith (天神信仰) — worship of the deified Michizane
        "de": "Tenjin-Glaube", "nl": "Tenjin-geloof", "sv": "Tenjin-tro",
        "es": "culto a Tenjin", "ca": "culte a Tenjin", "gl": "culto a Tenjin",
        "pt": "culto a Tenjin", "fr": "culte de Tenjin", "it": "culto di Tenjin",
        "ro": "cultul lui Tenjin", "ru": "культ Тэндзина", "uk": "культ Тендзіна",
        "pl": "kult Tenjina", "cs": "kult Tendžina",
    },
    "Q3952369": {  # Shinto sects and schools (神道の流派・教派)
        "de": "Shinto-Schulen und -Sekten", "nl": "shintoscholen en -sekten",
        "sv": "shintoskolor och -sekter", "es": "escuelas y sectas del sintoísmo",
        "ca": "escoles i sectes del xintoisme", "gl": "escolas e seitas do xintoísmo",
        "pt": "escolas e seitas do xintoísmo", "fr": "écoles et sectes du shintoïsme",
        "it": "scuole e sette dello shintoismo", "ro": "școli și secte ale șintoismului",
        "ru": "школы и секты синтоизма", "uk": "школи та секти синтоїзму",
        "pl": "szkoły i sekty shintō", "cs": "šintoistické školy a sekty",
    },
    "Q3271557": {  # imperial cult (君主崇拝)
        "de": "Herrscherkult", "nl": "heersercultus", "sv": "härskarkult",
        "es": "culto imperial", "ca": "culte imperial", "gl": "culto imperial",
        "pt": "culto imperial", "fr": "culte impérial", "it": "culto imperiale",
        "ro": "cult imperial", "ru": "культ императора", "uk": "культ імператора",
        "pl": "kult władcy", "cs": "císařský kult",
    },
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def existing_langs(qids):
    """{qid: set(langs with a label)} via one WDQS query."""
    values = " ".join(f"wd:{q}" for q in qids)
    q = (f"SELECT ?item ?lang WHERE {{ VALUES ?item {{ {values} }} "
         f"?item rdfs:label ?l . BIND(LANG(?l) AS ?lang) }}")
    for attempt in range(4):
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
            print(f"  [retry {attempt+1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed")


def main():
    _utf8()
    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE, encoding="utf-8")))

    todo = [q for q in TRANSLATIONS if q not in done]
    if not todo:
        print("nothing new — all authored concepts already done.")
        return
    print(f"{len(todo)} concept(s) this run: {todo}")
    have = existing_langs(todo)

    lines = []
    for qid in todo:
        for lang, label in TRANSLATIONS[qid].items():
            if lang not in have.get(qid, set()):        # non-destructive
                esc = label.replace('"', '""')
                lines.append(f'{qid}\tL{lang}\t"{esc}"')

    # append (don't clobber earlier runs)
    mode = "a" if os.path.exists(OUT) else "w"
    with open(OUT, mode, encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    done |= set(todo)
    json.dump(sorted(done), open(STATE, "w", encoding="utf-8"))
    remaining = "court ranks (rendering varies) + world-religion drift (already labelled)"
    print(f"Wrote {len(lines)} translation labels for {len(todo)} concepts -> {OUT}")
    print(f"Remaining tier: {remaining}")


if __name__ == "__main__":
    main()
