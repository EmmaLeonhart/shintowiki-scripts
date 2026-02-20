import requests
import json
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Additional shrine classifications to add
additional_qids = [
    'Q9610964',    # Myōjin Taisha
    'Q134917288',  # Shikinai Taisha
    'Q134917287',  # Shikinai Shosha
    'Q135160342',  # Kokuhei-sha
    'Q135160338',  # Kanpei-sha
    'Q135009152',  # Shrines receiving Hoe and Quiver
    'Q135009205',  # Shrines receiving Hoe offering
    'Q135009221',  # Shrines receiving Quiver offering
    'Q135009132',  # Shrine receiving Tsukinami-sai and Niiname-sai offerings
    'Q135009157',  # Shrine receiving Tsukinami-sai and Niiname-sai and Ainame-sai offerings
]

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Build query for these QIDs
values_clause = ' '.join([f'wd:{qid}' for qid in additional_qids])
query = f"""
SELECT ?item ?itemLabel WHERE {{
  VALUES ?item {{ {values_clause} }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
}}
"""

print("Fetching labels for additional shrine classifications...")
r = requests.get(WIKIDATA_SPARQL, params={
    'query': query,
    'format': 'json'
}, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

if r.status_code == 200:
    data = r.json()
    classifications = {}

    for binding in data['results']['bindings']:
        qid = binding['item']['value'].split('/')[-1]
        label = binding['itemLabel']['value']
        classifications[qid] = label
        print(f"{qid}: {label}")

    # Save to file
    with open('shrine_classifications.json', 'w', encoding='utf-8') as f:
        json.dump(classifications, f, ensure_ascii=False, indent=2)

    print(f"\nTotal classifications: {len(classifications)}")
    print("Saved to shrine_classifications.json")
else:
    print(f"Error: {r.status_code}")
    print(r.text)
