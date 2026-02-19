import requests
import json
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# First, get all court ranks in Japan (subclasses of Q99196082)
query1 = """
SELECT ?rank ?rankLabel WHERE {
  ?rank wdt:P279* wd:Q99196082 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
}
"""

print("Fetching court ranks...")
r = requests.get(WIKIDATA_SPARQL, params={
    'query': query1,
    'format': 'json'
}, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

if r.status_code == 200:
    data = r.json()
    court_ranks = {}
    for binding in data['results']['bindings']:
        qid = binding['rank']['value'].split('/')[-1]
        label = binding['rankLabel']['value']
        court_ranks[qid] = label
        print(f"{qid}: {label}")

    print(f"\nTotal court ranks found: {len(court_ranks)}")

    # Save to file for reference
    with open('court_ranks_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(court_ranks, f, ensure_ascii=False, indent=2)

    print("\nSaved to court_ranks_mapping.json")
else:
    print(f"Error: {r.status_code}")
    print(r.text)

# Now query for shrines with P11250 that have court rank P31 values
query2 = """
SELECT ?item ?itemLabel ?p11250 ?rank ?rankLabel WHERE {
  ?item wdt:P11250 ?p11250 .
  ?item wdt:P31 ?rank .
  ?rank wdt:P279* wd:Q99196082 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
}
"""

print("\n\nFetching shrines with court ranks...")
r = requests.get(WIKIDATA_SPARQL, params={
    'query': query2,
    'format': 'json'
}, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

if r.status_code == 200:
    data = r.json()
    shrines_by_rank = {}

    for binding in data['results']['bindings']:
        qid = binding['item']['value'].split('/')[-1]
        item_label = binding['itemLabel']['value']
        p11250 = binding['p11250']['value']
        rank_qid = binding['rank']['value'].split('/')[-1]
        rank_label = binding['rankLabel']['value']

        if rank_qid not in shrines_by_rank:
            shrines_by_rank[rank_qid] = []

        shrines_by_rank[rank_qid].append({
            'qid': qid,
            'label': item_label,
            'page': p11250,
            'rank_label': rank_label
        })

    # Print results organized by rank
    for rank_qid, shrines in shrines_by_rank.items():
        print(f"\n{rank_qid} ({court_ranks.get(rank_qid, 'Unknown')}): {len(shrines)} shrines")
        for shrine in shrines[:5]:  # Show first 5
            print(f"  - {shrine['page']} ({shrine['label']})")
        if len(shrines) > 5:
            print(f"  ... and {len(shrines) - 5} more")

    # Save to file
    with open('shrines_with_court_ranks.json', 'w', encoding='utf-8') as f:
        json.dump(shrines_by_rank, f, ensure_ascii=False, indent=2)

    print("\n\nSaved to shrines_with_court_ranks.json")
    print(f"Total unique ranks with shrines: {len(shrines_by_rank)}")
else:
    print(f"Error: {r.status_code}")
    print(r.text)
