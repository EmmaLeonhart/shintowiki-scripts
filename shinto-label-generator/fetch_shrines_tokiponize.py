"""
Fetch Japan shrine/temple items with source labels from Wikidata:
- Shinto shrines (instance/subclass path of Q845945), plus
- Buddhist temples in Japan (P31=Q5393308 and P17=Q17).
Source languages: Indonesian (id), Russian (ru), Ukrainian (uk), Lithuanian (lt).
Then strip bracket content, remove known shrine/temple prefixes,
tokiponize the remaining Japanese name, and produce
tomo sewi [suli] NAME output.
"""

import re
import csv
import sys
import io
import requests
from tokiponizer import tokiponize

# Windows UTF-8 console fix (guard against double-wrapping from imports)
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
elif hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT DISTINCT ?item ?itemLabel ?srcLabel ?srcLang ?jaLabel ?tokLabel WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }
  ?item rdfs:label ?srcLabel .
  BIND(LANG(?srcLabel) AS ?srcLang)
  FILTER(?srcLang IN ("id", "ru", "uk", "lt"))
  OPTIONAL { ?item rdfs:label ?tokLabel . FILTER(LANG(?tokLabel) = "tok") }
  OPTIONAL { ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?srcLabel
"""

def fetch_shrines():
    """Fetch target shrine/temple items with Indonesian labels from Wikidata."""
    print("Querying Wikidata SPARQL for Shinto shrines + Japan Buddhist temples with id/ru/uk/lt labels...")
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": SPARQL_QUERY, "format": "json"},
        headers={"User-Agent": "Japanese-Tokiponizer/1.0 (Shinto shrine label pipeline)"},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    results = data["results"]["bindings"]
    print(f"Got {len(results)} results from Wikidata.")
    return results

PREFIX_RULES = {
    "id": [
        ("Kuil Agung ", "Kuil Agung"),
        ("Kuil ", "Kuil"),
        ("Wihara Agung ", "Wihara Agung"),
        ("Wihara ", "Wihara"),
    ],
    "ru": [
        ("Великий храм ", "Temple Grand"),
        ("Храм ", "Temple"),
        ("Святилище ", "Shrine"),
    ],
    "uk": [
        ("Великий храм ", "Temple Grand"),
        ("Храм ", "Temple"),
        ("Святилище ", "Shrine"),
    ],
    "lt": [
        ("Didžioji šventykla ", "Temple Grand"),
        ("Šinto šventykla ", "Temple"),
        ("Šventykla ", "Temple"),
        ("Maldykla ", "Shrine"),
    ],
}

def process_label(source_lang, source_label):
    """
    Process a source-language shrine/temple label:
    1. Remove content in brackets (and the brackets themselves)
    2. Strip whitespace
    3. Detect language-specific shrine/temple prefix
    4. Remove prefix
    5. Remove spaces and dashes
    6. Decapitalize
    Returns (prefix, cleaned_name) or None if no valid prefix found.
    """
    # Remove bracketed content: (stuff), [stuff], {stuff}
    cleaned = re.sub(r'\([^)]*\)', '', source_label)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
    cleaned = cleaned.strip()

    # Detect prefix (case-insensitive for matching, preserve original tail)
    cleaned_lower = cleaned.lower()
    rules = PREFIX_RULES.get(source_lang, [])
    prefix = None
    name = None
    for raw_prefix, norm_prefix in rules:
        raw_prefix_lower = raw_prefix.lower()
        if cleaned_lower.startswith(raw_prefix_lower):
            prefix = norm_prefix
            name = cleaned[len(raw_prefix):]
            break

    if prefix is None:
        # Not a supported source-language shrine/temple prefix, skip
        return None

    # Remove spaces and dashes, decapitalize
    name = name.replace(" ", "").replace("-", "")
    name = name.lower()

    return (prefix, name)

def make_tokipona_label(prefix, tokiponized_name):
    """Build the toki pona label: tomo sewi [suli] NAME"""
    if prefix in ("Kuil Agung", "Wihara Agung", "Temple Grand"):
        return f"tomo sewi suli {tokiponized_name}"
    else:
        return f"tomo sewi {tokiponized_name}"

def write_quickstatements(rows, outdir="quickstatements"):
    """Write QuickStatements lines split by language into outdir/.
    Each file contains: QID<TAB>L<lang><TAB>\"label\".
    Returns dict of {lang: filepath} for files written."""
    import os
    os.makedirs(outdir, exist_ok=True)

    # Group rows by target language
    by_lang = {}
    for row in rows:
        lang = row.get("target_lang", "tok")
        by_lang.setdefault(lang, []).append(row)

    written = {}
    for lang, lang_rows in sorted(by_lang.items()):
        filepath = os.path.join(outdir, f"{lang}.txt")
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            for row in lang_rows:
                comment = f'# Source: {row["source_lang"]} "{row["source_label"]}"'
                if row.get("en_label"):
                    comment += f' | EN "{row["en_label"]}"'
                
                label = row["toki_pona_label"].replace('"', '""')
                f.write(f'{comment}\n')
                f.write(f'{row["qid"]}\tL{lang}\t"{label}"\n')
        written[lang] = filepath
    return written

def main():
    results = fetch_shrines()

    tok_labels_by_qid = {}
    for binding in results:
        qid = binding["item"]["value"].split("/")[-1]
        tok_label = binding.get("tokLabel", {}).get("value", "")
        if tok_label:
            tok_labels_by_qid.setdefault(qid, set()).add(tok_label)

    # Deduplicate SPARQL results: keep first (qid, source_lang, source_label) triple
    seen_qids = {}
    deduped = []
    for binding in results:
        qid = binding["item"]["value"].split("/")[-1]
        source_lang = binding["srcLang"]["value"]
        source_label = binding["srcLabel"]["value"]
        key = (qid, source_lang, source_label)
        if key not in seen_qids:
            seen_qids[key] = True
            deduped.append(binding)
    print(f"After dedup: {len(deduped)} unique (QID, source_lang, source_label) triples")

    rows = []
    seen_rows = set()
    skipped = 0

    for binding in deduped:
        qid = binding["item"]["value"].split("/")[-1]
        en_label = binding.get("itemLabel", {}).get("value", "")
        source_lang = binding["srcLang"]["value"]
        source_label = binding["srcLabel"]["value"]
        ja_label = binding.get("jaLabel", {}).get("value", "")
        existing_tok_labels = sorted(tok_labels_by_qid.get(qid, set()))
        has_tok_label = len(existing_tok_labels) > 0

        processed = process_label(source_lang, source_label)
        if processed is None:
            skipped += 1
            continue

        prefix, cleaned_name = processed
        variants = tokiponize(cleaned_name)

        for variant in variants:
            row_key = (qid, source_lang, source_label, variant)
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            tp_label = make_tokipona_label(prefix, variant)
            rows.append({
                "qid": qid,
                "en_label": en_label,
                "ja_label": ja_label,
                "source_lang": source_lang,
                "source_label": source_label,
                "prefix": prefix,
                "cleaned_input": cleaned_name,
                "target_lang": "tok",
                "tokiponized": variant,
                "toki_pona_label": tp_label,
                "has_tok_label": has_tok_label,
                "existing_tok_labels": " | ".join(existing_tok_labels),
            })

    # Write CSV
    outfile = "shrines_tokiponized.csv"
    with open(outfile, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "qid", "en_label", "ja_label", "source_lang", "source_label",
            "target_lang", "prefix", "cleaned_input", "tokiponized",
            "toki_pona_label", "has_tok_label", "existing_tok_labels",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Wrote {len(rows)} rows to {outfile}")
    print(f"Skipped {skipped} entries (no supported source-language prefix)")

    qs_rows = [row for row in rows if not row["has_tok_label"]]
    written = write_quickstatements(qs_rows)
    for lang, filepath in written.items():
        count = sum(1 for r in qs_rows if r.get("target_lang", "tok") == lang)
        print(f"Wrote {count} QuickStatements lines to {filepath}")

    # Print first few for quick review
    print("\n--- Sample output ---")
    for row in rows[:20]:
        print(f"  {row['qid']:12s} | {row['source_lang']:2s} | {row['source_label'][:36]:36s} -> {row['toki_pona_label']}")

if __name__ == "__main__":
    main()
