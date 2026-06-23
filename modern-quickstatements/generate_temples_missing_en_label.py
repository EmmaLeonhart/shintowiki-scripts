"""
generate_temples_missing_en_label.py
====================================
Temple analogue of ``generate_shrines_missing_en_label.py``. Produces a synced
worklist of every **Japanese Buddhist temple** on Wikidata (P31 = Q5393308,
country P17 = Q17 Japan) that has a Japanese label but NO English label, with the
name-in-kana reading (P1814) when present.

Scope is Japan-only by design (Emma, 2026-06-23): the Japanese -> English ->
multilingual label conventions only hold for Japanese temples. A temple in, e.g.,
Thailand should be rendered Japanese-independently by local convention, and its
English name does not propagate cleanly to the other languages, so it is excluded.

Bracket note: Wikidata labels should never contain bracketed disambiguators —
they are a labelling error. Downstream label generation strips bracket content
(full-width （）, half-width (), 〔〕) from the ``ja`` label before any
search / dedup / romanization. This script preserves the raw label; stripping
happens in ``temple_english.py`` so the raw value stays auditable here.

Output: ``temples_missing_en_label.json`` (alongside this script):
    {"generated_at": "...Z", "count": N,
     "items": [{"qid": "Q123", "ja": "金閣寺", "kana": "きんかくじ"}, ...]}
"""

import io
import json
import sys
from datetime import datetime, timezone

# Reuse the tested SPARQL transport (retries, 429-bail) from the shrine script.
from generate_shrines_missing_en_label import fetch_sparql

BUDDHIST_TEMPLE = "Q5393308"
JAPAN = "Q17"
OUTPUT_FILE = "temples_missing_en_label.json"


def _ensure_utf8_stdout():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def build_query():
    return f"""
    SELECT ?item ?ja ?kana WHERE {{
      ?item wdt:P31 wd:{BUDDHIST_TEMPLE} .
      ?item wdt:P17 wd:{JAPAN} .
      ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja")
      FILTER NOT EXISTS {{ ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?item wdt:P1814 ?kana . }}
    }}
    ORDER BY ?item
    """


def collapse(rows):
    """One entry per item, keeping the first kana reading seen."""
    items = {}
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        ja = r["ja"]["value"]
        kana = r.get("kana", {}).get("value", "")
        if qid not in items:
            items[qid] = {"qid": qid, "ja": ja, "kana": kana}
        elif kana and not items[qid]["kana"]:
            items[qid]["kana"] = kana
    return items


def main():
    _ensure_utf8_stdout()
    print("Querying Wikidata for Japanese Buddhist temples missing an English label...")
    rows = fetch_sparql(build_query())
    if rows is None:
        print("No results (timeout) — leaving existing list untouched.")
        return
    items = collapse(rows)
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "items": list(items.values()),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with_kana = sum(1 for i in items.values() if i["kana"])
    print(f"Wrote {len(items)} temples to {OUTPUT_FILE} ({with_kana} have a kana reading)")


if __name__ == "__main__":
    main()
