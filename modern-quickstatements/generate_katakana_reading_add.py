"""
generate_katakana_reading_add.py
================================
Step 1 of the top-level-katakana `P1814` replacement (queue item, Emma
2026-09-09): the ADD generator. GENERATOR ONLY — writes QuickStatements lines
into an atomic .txt file that the single daily submitter runs. It NEVER edits
Wikidata and the lines carry NO edit summaries. (CLAUDE.md "Wikidata editing —
ONE path only".)

## The population

`docs/katakana_name_in_kana_2026-09.md`, measured 2026-09-09: of 9,314 shrine
`P1814` statements, 772 are katakana-only, and 745 of those sit on items that
carry an Old-Japanese (ojp-hani) `P1448` official name. Those 745 belong to the
カミノヤシロ kana-qualifier pipeline, which relocates the reading onto the official
name and then strips the top-level statement.

**The remaining 27 statements on 26 items have no ojp-hani `P1448`, so nothing
in that pipeline can ever reach them** — every generator there keys on the item
having one. This script is what reaches them.

## The derivation

Emma, 2026-09-09: *"derive the Kana from the English-language labels combined
with whatever the standard transliteration is of the other stuff."* Every item
in the population already has an English label, which under CLAUDE.md IS the
reading — so the hiragana is built mechanically by `english_to_kana.kana_for`
(English label -> romanized stem, Japanese label -> shrine-type suffix) and is
never read out of an article or reasoned about.

`kana_for` refuses anything it cannot do confidently, and that refusal is doing
real work here rather than being defensive boilerplate — it is what keeps the
generator off the four items the docs have already ruled on:
  * `Q6543779` 四至神 / `ミヤノメグリノカミ` — ruled CORRECT as it stands
    (`docs/kana_name_mate_rulings.md`); a 〜神 item has no shrine-type suffix, so
    no suffix matches and nothing is emitted.
  * `Q10928586` 座摩神 — same shape.
  * `Q11474068` 岩井温泉 — an onsen, not a shrine, and already carrying
    `いわいおんせん`; no shrine-type suffix, nothing emitted.
  * `Q11352355` 一之宮神社 / `スサノオ` — a deity in a reading field, i.e. a wrong
    FIELD rather than a short reading. Its English label "Ichinomiya Shrine
    Yokohama" leaves a multi-word stem once the suffix is stripped, which
    `kana_for` refuses.

This script ONLY adds. The katakana is removed by the SEPARATE script
`generate_katakana_reading_remove.py`, which acts only after a fresh SPARQL
query confirms the derived hiragana is already on the item. Two separate
scripts, add first, remove later — never one action (CLAUDE.md).

⚠ The added statement carries NO reference. 22 of the 27 katakana statements are
referenced, and those references are references FOR THE KATAKANA — the value
being retired. A derived reading's provenance is the item's own English label,
which is not citable, so inventing a reference for it would be worse than
carrying none. Every other kana generator in this repo emits unreferenced
statements too.

Output: katakana_reading_add.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import io
import sys
import time
import requests

_usys.path.insert(0, _uos.path.dirname(_uos.path.abspath(__file__)))
from english_to_kana import kana_for

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "katakana_reading_add.txt"
SHRINE = "Q845945"

# The whole population in one query: every top-level P1814 on a shrine that has
# no ojp-hani official name, with both labels. Katakana-only is filtered client
# side — Blazegraph has no \p{IsHiragana}, which is why the measurement in
# docs/katakana_name_in_kana_2026-09.md was done this way too.
QUERY = f"""
SELECT ?item ?kana ?ja ?en WHERE {{
  ?item wdt:P31 wd:{SHRINE} ; p:P1814 ?st .
  ?st ps:P1814 ?kana .
  FILTER NOT EXISTS {{
    ?item p:P1448 ?ns . ?ns ps:P1448 ?on . FILTER(LANG(?on) = "ojp-hani")
  }}
  OPTIONAL {{ ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja") }}
  OPTIONAL {{ ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }}
}}
"""


class RateLimitError(Exception):
    """Raised on HTTP 429 — bail, no retries."""


_last = 0.0


def fetch_sparql(query, retries=3):
    global _last
    for attempt in range(1, retries + 1):
        elapsed = time.time() - _last
        if elapsed < 5:
            time.sleep(5 - elapsed)
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            _last = time.time()
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            print("SPARQL timed out after retries — exiting gracefully")
            return None
        _last = time.time()
        if r.status_code == 429:
            print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
            raise RateLimitError("429")
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def is_katakana(value):
    """A katakana-only reading: has katakana, no hiragana. Deliberately the same
    test the kana-qualifier pipeline uses, so the two populations are separated
    by the ojp-hani filter alone and not by two differing ideas of katakana."""
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def s(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def collect(rows):
    """Group the flat SPARQL rows into per-item records:
    {qid: {"ja": …, "en": …, "values": {…}}}."""
    items = {}
    for r in rows:
        q = qid(r["item"]["value"])
        rec = items.setdefault(q, {"ja": None, "en": None, "values": set()})
        rec["values"].add(r["kana"]["value"])
        if "ja" in r:
            rec["ja"] = r["ja"]["value"]
        if "en" in r:
            rec["en"] = r["en"]["value"]
    return items


def build_lines(items):
    """(lines, report). A report row is emitted for every katakana-bearing item,
    derivable or not, so a refusal is visible in the run log rather than
    vanishing into a shorter output file."""
    lines, report = [], []
    for q in sorted(items):
        rec = items[q]
        katakana = sorted(v for v in rec["values"] if is_katakana(v))
        if not katakana:
            continue
        derived = kana_for(rec["ja"], rec["en"])
        if not derived:
            report.append((q, katakana, rec["ja"], rec["en"], None, "no confident derivation"))
            continue
        if derived in rec["values"]:
            report.append((q, katakana, rec["ja"], rec["en"], derived, "already present"))
            continue
        lines.append(f"{q}|P1814|{s(derived)}")
        report.append((q, katakana, rec["ja"], rec["en"], derived, "add"))
    return lines, report


def main():
    print("=== Generate derived-hiragana P1814 ADD QuickStatements (no direct edits) ===\n")
    rows = fetch_sparql(QUERY)
    if rows is None:
        print("No SPARQL result — leaving the existing file untouched.")
        return
    items = collect(rows)
    lines, report = build_lines(items)

    for q, katakana, ja, en, derived, verdict in report:
        print(f"  {q:<12} {'/'.join(katakana):<26} {ja or '-':<24} "
              f"{en or '-':<52} -> {derived or '-'}  [{verdict}]")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable,
        # so emitting in result order rewrites the whole file on every build.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    print(f"\nWrote {len(lines)} lines to {OUTPUT_FILE} "
          f"({len(report)} katakana-bearing items seen)")


if __name__ == "__main__":
    main()
