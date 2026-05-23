"""
Generate proposed Indonesian labels for Japanese-only shrines/temples.
1. Query Wikidata for items with 'ja' label but NO 'id' label.
2. Fetch 'ja' label, 'en' label (if any), and optional Kana reading (P1814/P5461).
3. Convert to Romaji (Hepburn) using pykakasi.
4. Strip common shrine/temple suffixes to avoid redundancy in "Kuil [Name]".
5. Output to 'proposed_indonesian_labels.csv' and 'quickstatements/id_proposed.txt'.
"""

import os
import sys
import csv
import re
import requests
import pykakasi

# Initialize pykakasi (v2.3.0 API)
kks = pykakasi.kakasi()

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_SHRINES = """
SELECT DISTINCT ?item ?jaLabel ?enLabel ?kanaName ?kanaReading WHERE {
  ?item wdt:P31/wdt:P279* wd:Q845945 .
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id") }
  OPTIONAL { ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en") }
  OPTIONAL { ?item wdt:P1814 ?kanaName . }
  OPTIONAL { ?item wdt:P5461 ?kanaReading . }
}
"""

SPARQL_TEMPLES = """
SELECT DISTINCT ?item ?jaLabel ?enLabel ?kanaName ?kanaReading WHERE {
  ?item wdt:P31 wd:Q5393308 .
  ?item wdt:P17 wd:Q17 .
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id") }
  OPTIONAL { ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en") }
  OPTIONAL { ?item wdt:P1814 ?kanaName . }
  OPTIONAL { ?item wdt:P5461 ?kanaReading . }
}
"""

def fetch_candidates():
    results = []
    print("Querying Wikidata for Japanese-only Shrines...")
    try:
        r = requests.get(SPARQL_ENDPOINT, params={"query": SPARQL_SHRINES, "format": "json"}, headers={"User-Agent": "Japanese-Tokiponizer/1.0"}, timeout=300)
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
        for b in bindings:
            b["type"] = {"value": "shrine"}
            results.append(b)
    except Exception as e: print(f"Error fetching shrines: {e}")

    print("Querying Wikidata for Japanese-only Temples...")
    try:
        r = requests.get(SPARQL_ENDPOINT, params={"query": SPARQL_TEMPLES, "format": "json"}, headers={"User-Agent": "Japanese-Tokiponizer/1.0"}, timeout=300)
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
        for b in bindings:
            b["type"] = {"value": "temple"}
            results.append(b)
    except Exception as e: print(f"Error fetching temples: {e}")
    return results

def to_romaji(text):
    cleaned = re.sub(r'\(.*?\)|（.*?）', '', text).strip()
    result = kks.convert(cleaned)
    # Get Hepburn, join parts
    name = " ".join([item['hepburn'] for item in result]).title()
    
    # Normalize macrons for Indonesian (nearly 1-1 with Hepburn but usually no macrons)
    name = name.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    # Also handle the 'uu' / 'ou' patterns that sometimes appear from pykakasi if not in Hepburn mode
    name = name.replace("uu", "u").replace("ou", "o").replace("aa", "a").replace("ii", "i").replace("ee", "e")

    # Strip common Japanese shrine/temple suffixes to avoid redundancy in "Kuil [Name]"
    # Added common variants and case sensitivity handled by .title() previously
    suffixes = [
        " Jinja", " Jingu", " Taisha", " Tenmangu", " Gu", 
        " Ji", " Tera", " Dera", " In", " An", " Miya", " Yashiro"
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    return name

def main():
    results = fetch_candidates()
    proposals = []
    print("Processing items...")
    for binding in results:
        qid = binding["item"]["value"].split("/")[-1]
        ja_label = binding["jaLabel"]["value"]
        en_label = binding.get("enLabel", {}).get("value", "")
        source_text = binding.get("kanaName", {}).get("value") or binding.get("kanaReading", {}).get("value") or ja_label
        item_type = binding["type"]["value"]
        
        try:
            name = to_romaji(source_text)
            if not name: continue
            
            prefix = "Kuil" if item_type == "shrine" else "Wihara"
            proposed_label = f"{prefix} {name}"
            
            proposals.append({
                "qid": qid,
                "ja_label": ja_label,
                "en_label": en_label,
                "romaji": name,
                "type": item_type,
                "proposed_label": proposed_label
            })
        except Exception as e:
            print(f"Error processing {qid}: {e}")

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
    main()
