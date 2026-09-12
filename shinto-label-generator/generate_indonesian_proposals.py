"""
Generate proposed Indonesian labels for shrines/temples that have none.

⭐ DERIVED FROM THE ENGLISH LABEL, not from the kanji. Emma, 2026-09-10: *"the
Indonesian labels often appear quite dubious and I'm not sure how they were
derived. They should be derived from the proposed English labels for the
shrines."*

## What it used to do, and why the output was junk

It fetched the English label and used it ONLY in a `# Source:` comment. The label
itself was `pykakasi(kana or ja_label)` — a reading guessed off the kanji — then
macron-stripped and blanket-collapsed (`uu`/`ou`/`aa`/`ii`/`ee` -> one vowel), then
had a suffix chopped off a glued-together string. Shrine names take irregular
local readings, so pykakasi on kanji is a guess, and the collapse corrupted what
survived:

    元八幡        EN "Moto Hachiman"        ->  Kuil Genpachi Hata
    藤崎八旛宮     EN "Fujisaki Hachimangū"  ->  Kuil Fujisaki Hachi Hata
    陶山神社       EN "Tōzan Shrine"         ->  Kuil Sueyamajinja AND Kuil Tozanjinja
    柞原八幡宮     EN "Yusuhara Hachimangū"  ->  Kuil Yusuharahachimangu

Every one of those had the right answer sitting in the English label.

## The convention, read off the corpus

Measured 2026-09-11 over the **24,460** shrines that already carry both an id and
an en label — this is the community's own house style, not a guess:

| en label | id label | follows | other |
|---|---|---|---|
| `X Shrine` | `Kuil X` | **20,520** | 253 |
| ends in a small transliterated suffix (`Tenmangū`, `Hachimangū`, `-gū`, `Tōshō-gū`, `Hachiman`) | `Kuil <the whole label>` | **1,449** | 27 |
| ends in `Jingū` / `Taisha` / `Daijingū` | `Kuil Agung X` | 46 | 53 — *Emma's ruling, not the count* |

So:

  * **`Kuil` + the label with the word "Shrine" removed** is the rule.
  * **A transliterated Japanese suffix is part of the name and stays.** CLAUDE.md:
    "The ending is part of the name. 社 ≠ 神社 ≠ 宮."
  * **Macrons are KEPT** — 623 of the sampled id labels carry one, and
    `Kuil Ueno Tenmangū` / `Kuil Ueno Ōji` are the corpus form. The old
    macron-stripping was simply wrong.
  * **A parenthetical disambiguator is KEPT**: `Ueno Ōji Shrine (Osaka)` ->
    `Kuil Ueno Ōji (Osaka)`.
  * ⭐ **`Jingū` / `Taisha` / `Daijingū` become `Kuil Agung X`** — the suffix is
    dropped and the grand-shrine sense is translated. 53 against 46 is a corpus
    disagreeing with itself, so this was refused until **Emma ruled on
    2026-09-11**: `Ise Jingū` -> `Kuil Agung Ise`, `Izumo Taisha` ->
    `Kuil Agung Izumo`. It is a ruling, not a reading of the corpus — do not
    "correct" it back to the majority form.

## Source of the English label

The item's own en label where Wikidata has one; otherwise the proposal our own
en-label pipeline has already staged (`modern-quickstatements/*en_labels*.txt`),
which is what "the PROPOSED English labels" means. An item with neither gets
NOTHING — deriving from the kanji is what produced `Kuil Genpachi Hata`.

Output: 'proposed_indonesian_labels.csv' and 'quickstatements/id_proposed.txt'.
"""

import io
import os
import sys
import csv
import re
from collections import Counter
import requests
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

# pykakasi is GONE. Reading the kanji is what produced "Kuil Genpachi Hata";
# the English label is the source now, so there is nothing left to transliterate.

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"

SPARQL_SHRINES = """
SELECT DISTINCT ?item ?jaLabel ?enLabel WHERE {
  ?item wdt:P31/wdt:P279* wd:Q845945 .
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id") }
  OPTIONAL { ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en") }
}
"""

SPARQL_TEMPLES = """
SELECT DISTINCT ?item ?jaLabel ?enLabel WHERE {
  ?item wdt:P31 wd:Q5393308 .
  ?item wdt:P17 wd:Q17 .
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id") }
  OPTIONAL { ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en") }
}
"""

def fetch_candidates():
    results = []
    print("Querying Wikidata for Japanese-only Shrines...")
    try:
        wd_pace(SPARQL_INTERVAL)
        r = requests.get(SPARQL_ENDPOINT, params={"query": SPARQL_SHRINES, "format": "json"}, headers={"User-Agent": WIKIDATA_USER_AGENT}, timeout=300)
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
        for b in bindings:
            b["type"] = {"value": "shrine"}
            results.append(b)
    except Exception as e: print(f"Error fetching shrines: {e}")

    print("Querying Wikidata for Japanese-only Temples...")
    try:
        wd_pace(SPARQL_INTERVAL)
        r = requests.get(SPARQL_ENDPOINT, params={"query": SPARQL_TEMPLES, "format": "json"}, headers={"User-Agent": WIKIDATA_USER_AGENT}, timeout=300)
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
        for b in bindings:
            b["type"] = {"value": "temple"}
            results.append(b)
    except Exception as e: print(f"Error fetching temples: {e}")
    return results

# A transliterated Japanese shrine suffix is part of the NAME and stays in the
# label (corpus: 1,449 against 27). Longest first so Tōshō-gū is not read as -gū.
KEEP_SUFFIXES = [
    "Tōshō-gū", "Tosho-gu", "Tōshōgū", "Toshogu",
    "Hachimangū", "Hachimangu", "Hachiman-gū", "Hachiman-gu",
    "Tenmangū", "Tenmangu", "Tenman-gū", "Tenman-gu",
    "Tenjinsha", "Tenjin-sha", "Hachiman",
    "-no-miya", "no-miya", "-miya", "Jinja", "-gū", "-gu", "-sha",
]

# A grand-shrine suffix. The corpus splits 53 `Kuil <whole>` against 46
# `Kuil Agung X`, so this was refused until Emma ruled on 2026-09-11: the suffix
# is TRANSLATED, not carried — drop it and mark the sense with Agung ("grand").
AGUNG_SUFFIXES = ["Daijingū", "Daijingu", "daijingū", "daijingu",
                  "Jingū", "Jingu", "Taisha", "taisha"]

# Left behind when a suffix is stripped off a hyphenated name: "Izumo-daijingū".
_STEM_TAIL = "-–— 	"

_PAREN_TAIL = re.compile(r"\s*\([^)]*\)\s*$")

# Forbidden whitespace, per tests/test_label_whitespace.py. It arrives from the
# ENGLISH labels — "Wakamiya Hachiman Shrine", "Aijikaue Shrine (Legendary
# Site C)" — so deriving faithfully carries a defect through. Folded to a
# single ordinary space here; the en label itself is a separate problem.
_BAD_SPACE = re.compile(r"[   	]+")

# An English label that is a DESCRIPTION rather than a name. "Co-Enshrinement of
# Ohowano Shrine" derives "Kuil Co-Enshrinement of Ohowano", which is faithful to
# the English and still junk — exactly the "shit Indonesian labels" complaint.
# A Japanese shrine name romanises without English function words, so their
# presence means the label is prose.
_GLOSS = re.compile(r"(?:^|\s)(?:of|the|and|for|at|in|on|to)(?:\s|$)"
                    r"|Legendary|Site|Co-Enshrinement|Unknown|Former|Possible",
                    re.I)


def indonesian_label(en, kind):
    """(label, reason). The Indonesian label for an English one, or (None, why).

    `kind` is "shrine" or "temple", which chooses Kuil / Wihara.
    """
    en = (en or "").strip()
    if not en:
        return None, "no English label to derive from"
    if "," in en:
        # 'Kawahara Shrine, Nagoya' is 'Kuil Kawahara' in the corpus — the comma
        # disambiguator is dropped, not carried like a parenthetical one. One
        # example is not a rule, so rather than guess which, refuse.
        return None, "comma disambiguator — corpus drops it, not carried here"

    en = _BAD_SPACE.sub(" ", en).strip()
    if _GLOSS.search(en):
        return None, "English label is a gloss, not a name"

    prefix = "Kuil" if kind == "shrine" else "Wihara"
    word = " Shrine" if kind == "shrine" else " Temple"

    # The generic word usually ends the label, but sometimes sits before a
    # parenthetical: 'Ueno Ōji Shrine (Osaka)'. Remove the WORD and keep the rest,
    # which is what the corpus does.
    bare = _PAREN_TAIL.sub("", en)
    tail = en[len(bare):]
    if bare.endswith(word):
        stem = bare[: -len(word)].strip()
        if not stem:
            return None, "the generic word alone"
        return f"{prefix} {stem}{tail}", "ok"

    for suf in AGUNG_SUFFIXES:
        if bare.endswith(suf):
            stem = bare[: -len(suf)].rstrip(_STEM_TAIL).strip()
            if not stem:
                return None, "the grand-shrine word alone"
            return f"{prefix} Agung {stem}{tail}", "ok (Agung)"

    for suf in sorted(KEEP_SUFFIXES, key=len, reverse=True):
        if bare.endswith(suf):
            return f"{prefix} {en}", "ok (suffix kept)"

    return None, "English label ends in no known shrine/temple word"


def load_en_proposals():
    """{qid: proposed en label} from our own en-label batches.

    "The PROPOSED English labels" — an item whose en label has been generated but
    not yet delivered by the drip is still an item whose English name we know.
    """
    mq = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "modern-quickstatements")
    out = {}
    pat = re.compile(r'^(Q\d+)[|	]L(?:en|EN)[|	]"(.*)"\s*$')
    for name in sorted(os.listdir(mq)) if os.path.isdir(mq) else []:
        if not name.endswith(".txt") or "en_label" not in name:
            continue
        for line in open(os.path.join(mq, name), encoding="utf-8"):
            m = pat.match(line.strip())
            if m:
                out.setdefault(m.group(1), m.group(2).replace('""', '"'))
    return out


def main():
    results = fetch_candidates()
    staged = load_en_proposals()
    print(f"{len(staged)} English labels staged but not yet delivered — usable as "
          f"the 'proposed' English label")
    proposals = []
    reasons = Counter()
    print("Processing items...")
    for binding in results:
        qid = binding["item"]["value"].split("/")[-1]
        ja_label = binding["jaLabel"]["value"]
        # The item's own en label, else the one our pipeline has already staged.
        # NEVER the kanji: reading it with pykakasi is what produced
        # "Kuil Genpachi Hata" for 元八幡 / "Moto Hachiman".
        en_label = binding.get("enLabel", {}).get("value", "") or staged.get(qid, "")
        item_type = binding["type"]["value"]

        proposed_label, reason = indonesian_label(en_label, item_type)
        reasons[reason] += 1
        if not proposed_label:
            continue
        proposals.append({
            "qid": qid,
            "ja_label": ja_label,
            "en_label": en_label,
            "romaji": proposed_label.split(" ", 1)[1],
            "type": item_type,
            "proposed_label": proposed_label,
        })

    print("\nderivation outcomes:")
    for reason, n in reasons.most_common():
        print(f"  {n:>6}  {reason}")

    # Deterministic order, keyed on the QID.
    #
    # Without this the output order is the SPARQL row order, and this is the one label
    # generator whose query carries NO `ORDER BY` -- so WDQS returns an arbitrary
    # permutation each run and every CI regeneration commits the whole file as changed.
    # Measured 2026-08-20: 77,980 insertions against 77,980 deletions, identical content,
    # `set(old) == set(new)` and `old != new`, on id_proposed.txt AND its rendered
    # id_proposed.html.
    #
    # That churn is not just noise -- it is camouflage. When a regeneration diff is always
    # six figures, nobody reads it, and the two days these pipelines were dead the diff
    # dropped to a one-line date stamp, which read as "nothing needed regenerating".
    #
    # Sorted here rather than in the query on purpose: this makes the ordering a property
    # of the writer, so it survives an endpoint that ignores ORDER BY and a future edit to
    # the query. Sorting the FILE afterwards would not work -- each statement is preceded
    # by its own `# Source:` comment line, and a line sort divorces the two.
    proposals.sort(key=lambda p: (int(p["qid"][1:]) if p["qid"][1:].isdigit() else 0,
                                  p["qid"]))

    # Write CSV
    with open("proposed_indonesian_labels.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["qid", "ja_label", "en_label", "romaji", "type", "proposed_label"])
        writer.writeheader()
        writer.writerows(proposals)
    
    # Write QuickStatements with comments
    qs_file = os.path.join("quickstatements", "id_proposed.txt")
    with open(qs_file, "w", encoding="utf-8", newline="\n") as f:
        for p in proposals:
            comment = f'# Source: JA "{p["ja_label"]}"'
            if p["en_label"]: comment += f' | EN "{p["en_label"]}"'
            comment += f' -> Indonesian "{p["proposed_label"]}"'
            f.write(f'{comment}\n{p["qid"]}\tLid\t"{p["proposed_label"]}"\n')
    print(f"Wrote {len(proposals)} proposals to {qs_file}")

if __name__ == "__main__":
    # Rebound HERE, not inside main(): the determinism tests call main()
    # directly, and replacing pytest's captured stdout closes it and breaks
    # every test after this one. Needed at all because the refusal reasons
    # name Jingū and Taisha, which cp1252 cannot encode.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
