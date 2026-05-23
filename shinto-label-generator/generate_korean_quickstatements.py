"""
Generate Korean (ko) labels for Shinto shrines and Buddhist temples.

Two paths:
- Japan shrines with Indonesian labels: strip prefix → koreanize → append Korean suffix
- All other shrines with Japanese labels: hanja.translate() for sino-Korean reading

Output: quickstatements/ko.txt
"""

import os
import sys
import io
import re
import requests
import hanja
from koreanizer import koreanize
from fetch_shrines_tokiponize import process_label

# Windows UTF-8 console fix (guard against double-wrapping from imports)
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
elif hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Query 1: Japan shrines with Indonesian labels (for koreanize path)
SPARQL_ID = """
SELECT DISTINCT ?item ?idLabel ?jaLabel WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }
  ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id")
  OPTIONAL { ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja") }
  FILTER NOT EXISTS { ?item rdfs:label ?koLabel . FILTER(LANG(?koLabel) = "ko") }
}
ORDER BY ?item
"""

# Query 2: Shrines with Japanese labels but no Indonesian label (hanja fallback)
SPARQL_JA = """
SELECT DISTINCT ?item ?jaLabel WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id") }
  FILTER NOT EXISTS { ?item rdfs:label ?koLabel . FILTER(LANG(?koLabel) = "ko") }
}
ORDER BY ?item
"""

# Indonesian prefix → Korean suffix mapping
KOREAN_SUFFIX = {
    "Kuil":        "신사",      # shrine
    "Kuil Agung":  "대신사",    # grand shrine
    "Wihara":      "사원",      # temple
    "Wihara Agung": "대사원",   # grand temple
}


def run_sparql(query, label):
    """Run a SPARQL query and return results."""
    print(f"Querying Wikidata: {label}...")
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={"User-Agent": "Japanese-Tokiponizer/1.0 (Korean label pipeline)"},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    results = data["results"]["bindings"]
    print(f"  Got {len(results)} results.")
    return results


def japanese_to_korean_hanja(ja_label):
    """Convert a Japanese kanji label to Korean using sino-Korean readings.

    Uses the hanja library to get Korean readings of CJK characters.
    Kana characters are transliterated via koreanize().
    """
    if not ja_label:
        return None

    result_parts = []
    current_kana = []
    current_kanji = []

    for char in ja_label:
        if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF':
            # Hiragana or Katakana
            if current_kanji:
                kanji_str = "".join(current_kanji)
                translated = hanja.translate(kanji_str, "substitution")
                result_parts.append(translated)
                current_kanji = []
            current_kana.append(char)
        elif '\u4E00' <= char <= '\u9FFF' or '\u3400' <= char <= '\u4DBF':
            # CJK Unified Ideograph
            if current_kana:
                kana_str = "".join(current_kana)
                result_parts.append(koreanize(kana_str))
                current_kana = []
            current_kanji.append(char)
        else:
            if current_kanji:
                kanji_str = "".join(current_kanji)
                translated = hanja.translate(kanji_str, "substitution")
                result_parts.append(translated)
                current_kanji = []
            if current_kana:
                kana_str = "".join(current_kana)
                result_parts.append(koreanize(kana_str))
                current_kana = []

    if current_kanji:
        kanji_str = "".join(current_kanji)
        translated = hanja.translate(kanji_str, "substitution")
        result_parts.append(translated)
    if current_kana:
        kana_str = "".join(current_kana)
        result_parts.append(koreanize(kana_str))

    result = "".join(result_parts)
    # If hanja couldn't translate (returned original kanji), return None
    if any('\u4E00' <= c <= '\u9FFF' or '\u3400' <= c <= '\u4DBF' for c in result):
        return None
    return result if result else None


def main():
    rows = []
    seen_qids = set()
    skipped = 0

    # --- Path 1: Shrines with Indonesian labels → koreanize ---
    id_results = run_sparql(SPARQL_ID, "shrines with Indonesian labels, no Korean")

    for binding in id_results:
        qid = binding["item"]["value"].split("/")[-1]
        if qid in seen_qids:
            continue
        seen_qids.add(qid)

        id_label = binding["idLabel"]["value"]
        ja_label = binding.get("jaLabel", {}).get("value", "")

        processed = process_label("id", id_label)
        if processed is None:
            # Indonesian label didn't match known prefix — try hanja fallback
            if ja_label:
                ko_label = japanese_to_korean_hanja(ja_label)
                if ko_label:
                    rows.append({
                        "qid": qid, 
                        "ko_label": ko_label, 
                        "comment": f'# Source: JA "{ja_label}" (hanja reading fallback)'
                    })
                else:
                    skipped += 1
            else:
                skipped += 1
            continue

        prefix, cleaned_name = processed
        suffix = KOREAN_SUFFIX.get(prefix, "신사")
        korean_name = koreanize(cleaned_name)
        if korean_name:
            rows.append({
                "qid": qid, 
                "ko_label": f"{korean_name} {suffix}",
                "comment": f'# Source: ID "{id_label}" (romanization)'
            })
        else:
            skipped += 1

    print(f"After Indonesian path: {len(rows)} labels generated")

    # --- Path 2: Shrines with Japanese labels only → hanja ---
    ja_results = run_sparql(SPARQL_JA, "shrines with Japanese labels only, no Korean")

    for binding in ja_results:
        qid = binding["item"]["value"].split("/")[-1]
        if qid in seen_qids:
            continue
        seen_qids.add(qid)

        ja_label = binding["jaLabel"]["value"]
        ko_label = japanese_to_korean_hanja(ja_label)
        if ko_label:
            rows.append({
                "qid": qid, 
                "ko_label": ko_label,
                "comment": f'# Source: JA "{ja_label}" (hanja reading)'
            })
        else:
            skipped += 1

    print(f"After both paths: {len(rows)} labels generated")

    # Write QuickStatements
    outdir = "quickstatements"
    os.makedirs(outdir, exist_ok=True)
    filepath = os.path.join(outdir, "ko.txt")
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            label = row["ko_label"].replace('"', '""')
            f.write(f'{row["comment"]}\n')
            f.write(f'{row["qid"]}\tLko\t"{label}"\n')

    print(f"\nDone! Wrote {len(rows)} Korean QuickStatements to {filepath}")
    print(f"Skipped {skipped} items (no translatable label)")

    # Sample output
    print("\n--- Sample output ---")
    for row in rows[:20]:
        print(f"  {row['qid']:12s} | {row['ko_label']}")


if __name__ == "__main__":
    main()
