import requests
import json
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Get all ACTUAL court ranks (instances of court rank in Japan OR subclasses)
query = """
SELECT DISTINCT ?rank ?rankLabel WHERE {
  {
    # Instances of court rank in Japan
    ?rank wdt:P31 wd:Q99196082 .
  } UNION {
    # Subclasses of court rank in Japan
    ?rank wdt:P279 wd:Q99196082 .
  } UNION {
    # Instances of subclasses
    ?rank wdt:P31/wdt:P279* wd:Q99196082 .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
}
"""

print("Fetching all court ranks from Wikidata...", flush=True)
r = requests.get(WIKIDATA_SPARQL, params={
    'query': query,
    'format': 'json'
}, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

if r.status_code == 200:
    data = r.json()
    court_ranks = {}

    for binding in data['results']['bindings']:
        qid = binding['rank']['value'].split('/')[-1]
        label = binding['rankLabel']['value']
        court_ranks[qid] = label
        print(f"{qid}: {label}", flush=True)

    # Save to file
    with open('court_ranks_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(court_ranks, f, ensure_ascii=False, indent=2)

    print(f"\nTotal court ranks found: {len(court_ranks)}", flush=True)
    print("Saved to court_ranks_mapping.json", flush=True)
else:
    print(f"Error: {r.status_code}", flush=True)
    print(r.text, flush=True)
