#!/usr/bin/env python3
"""
Fetch all Wikidata property English labels using SPARQL query.
Creates a CSV cache file: property_labels_cache.csv

This is MUCH more efficient than querying properties individually.
Uses a single SPARQL query to get all properties at once.
"""

import requests
import csv
import sys
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wikidata SPARQL endpoint
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

# SPARQL query to get all property labels in English
SPARQL_QUERY = """
SELECT ?property ?label WHERE {
  ?property a wikibase:Property .
  ?property rdfs:label ?label .
  FILTER(LANG(?label) = "en")
}
"""

OUTPUT_FILE = 'property_labels_cache.csv'

def fetch_property_labels():
    """Fetch all Wikidata property labels using SPARQL."""
    print("Querying Wikidata SPARQL endpoint for all property labels...")
    print("This may take a minute or two...\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/sparql-results+json'
    }

    params = {
        'query': SPARQL_QUERY
    }

    try:
        response = requests.get(SPARQL_ENDPOINT, params=params, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()

        if 'results' not in data or 'bindings' not in data['results']:
            print("ERROR: Unexpected response format from SPARQL endpoint")
            return False

        bindings = data['results']['bindings']
        print(f"Retrieved {len(bindings)} properties from Wikidata")

        # Parse results and create mapping
        property_labels = {}
        for binding in bindings:
            if 'property' in binding and 'label' in binding:
                property_uri = binding['property']['value']
                label = binding['label']['value']

                # Extract property ID from URI (e.g., http://www.wikidata.org/entity/P31 -> P31)
                prop_id = property_uri.split('/')[-1]
                property_labels[prop_id] = label

        print(f"Parsed {len(property_labels)} unique properties\n")

        # Save to CSV
        print(f"Writing to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['property_id', 'label'])
            writer.writeheader()
            for prop_id in sorted(property_labels.keys()):
                writer.writerow({
                    'property_id': prop_id,
                    'label': property_labels[prop_id]
                })

        print(f"Successfully created cache file: {OUTPUT_FILE}")
        print(f"Total properties cached: {len(property_labels)}\n")
        return True

    except Exception as e:
        print(f"ERROR fetching property labels: {e}")
        return False

def main():
    print("=" * 70)
    print("WIKIDATA PROPERTY LABELS CACHE GENERATOR")
    print("=" * 70)
    print()

    success = fetch_property_labels()

    if success:
        print("Cache generation COMPLETE")
        print("\nYou can now use this cache in generate_shikinaisha_pages scripts")
        print("by loading property_labels_cache.csv instead of querying Wikidata")
    else:
        print("Cache generation FAILED")
        sys.exit(1)

if __name__ == '__main__':
    main()
