#!/usr/bin/env python3
"""
Batch deprecate Engishiki-related properties on Shikinai Ronsha shrines.
Uses SPARQL to find all shrines with P31 Shikinai Ronsha (Q135022904) and processes them.
Limit: 50 shrines per run (to allow for review before full batch).
"""

import requests
import sys
import io
import time

# Handle Unicode on Windows - do this before imports
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Import the deprecation module
from deprecate_engishiki_shrine_properties import (
    login, get_entity, check_p460_property, add_role_qualifier,
    deprecate_property_statements, session
)

# Configuration
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Target: Shikinai Ronsha shrines
SHIKINAI_RONSHA_QID = "Q135022904"
LIMIT = 50

def get_shikinai_ronsha_shrines(limit=50):
    """Query SPARQL to get all shrines with P31 Shikinai Ronsha"""
    sparql_query = f"""
    SELECT ?shrine ?shrineLabel WHERE {{
      ?shrine wdt:P31 wd:{SHIKINAI_RONSHA_QID} .
      ?shrine wdt:P460 ?same_as .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT {limit}
    """

    print(f"Querying SPARQL for Shikinai Ronsha shrines (limit: {limit})...")
    r = requests.get(SPARQL_ENDPOINT, params={
        'query': sparql_query,
        'format': 'json'
    })

    results = r.json()['results']['bindings']
    shrine_qids = [item['shrine']['value'].split('/')[-1] for item in results]
    shrine_labels = [item['shrineLabel']['value'] for item in results]

    print(f"Found {len(shrine_qids)} shrines:\n")
    for qid, label in zip(shrine_qids, shrine_labels):
        print(f"  - {label} ({qid})")

    return shrine_qids, shrine_labels

def process_shrine(shrine_qid, shrine_label, index, total):
    """Process a single shrine and return result"""
    print(f"\n[{index}/{total}] Processing: {shrine_label} ({shrine_qid})")

    try:
        # Get the target shrine
        entity = get_entity(shrine_qid)

        # Check P460 property
        p460_qid = check_p460_property(entity)

        if not p460_qid:
            print(f"  ⊘ No valid P460 - skipped")
            return False

        # Add role qualifier to P460
        add_role_qualifier(shrine_qid, p460_qid)

        # Deprecate properties
        deprecate_property_statements(shrine_qid, p460_qid)

        print(f"  ✓ Successfully processed")
        return True

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False

def main():
    """Main script execution"""
    print("=" * 70)
    print("Batch Deprecation Script - Shikinai Ronsha Shrines")
    print("=" * 70)
    print()

    # Get shrines from SPARQL
    shrine_qids, shrine_labels = get_shikinai_ronsha_shrines(LIMIT)

    if not shrine_qids:
        print("No shrines found. Exiting.")
        return

    print()
    print("=" * 70)
    print(f"Ready to process {len(shrine_qids)} shrines")
    print("=" * 70)
    print()
    print("IMPORTANT: Please review the list above before continuing.")
    print("This will deprecate Engishiki-related properties on all listed shrines.")
    print()
    response = input("Continue with deprecation? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("Aborted by user.")
        return

    # Login before processing
    print()
    login()

    # Process each shrine
    print()
    print("=" * 70)
    print(f"Processing {len(shrine_qids)} shrines...")
    print("=" * 70)

    processed = 0
    skipped = 0
    errors = 0

    for i, (shrine_qid, shrine_label) in enumerate(zip(shrine_qids, shrine_labels), 1):
        try:
            result = process_shrine(shrine_qid, shrine_label, i, len(shrine_qids))
            if result:
                processed += 1
            else:
                skipped += 1
            time.sleep(1)  # Rate limiting between shrines
        except Exception as e:
            print(f"  ✗ Unexpected error: {str(e)}")
            errors += 1

    # Summary
    print()
    print("=" * 70)
    print("Batch processing complete")
    print("=" * 70)
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print(f"Total: {processed + skipped + errors}")

if __name__ == '__main__':
    main()
