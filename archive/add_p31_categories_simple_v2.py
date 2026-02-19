import mwclient
import requests
import time
import json
import re
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Load court ranks and shrine classifications
with open('court_ranks_mapping.json', 'r', encoding='utf-8') as f:
    court_ranks = json.load(f)

with open('shrine_classifications.json', 'r', encoding='utf-8') as f:
    shrine_classifications = json.load(f)

# Combine all P31 values we're interested in
all_p31_classifications = {**court_ranks, **shrine_classifications}

print(f"Loaded {len(all_p31_classifications)} P31 classifications to check", flush=True)

# Get all pages from Category:Pages linked to Wikidata
print("\nFetching pages from Category:Pages linked to Wikidata...", flush=True)
category = site.pages['Category:Pages linked to Wikidata']

edit_count = 0
page_count = 0

for page in category:
    if page.namespace != 0:  # Main namespace only
        continue

    page_count += 1
    print(f"\n[{page_count}] {page.name}", flush=True)

    # Extract QID from page
    try:
        text = page.text()
    except Exception as e:
        print(f"  Error reading page: {e}", flush=True)
        if "429" in str(e):
            print(f"  Rate limited, waiting 60 seconds...", flush=True)
            time.sleep(60)
            try:
                text = page.text()
            except:
                print(f"  Still rate limited, skipping", flush=True)
                continue
        else:
            continue

    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)

    if not match:
        print(f"  No QID found, skipping", flush=True)
        continue

    qid = match.group(1)
    print(f"  QID: {qid}", flush=True)

    # Query Wikidata for P31 values
    query = f"""
    SELECT ?p31 ?p31Label WHERE {{
      wd:{qid} wdt:P31 ?p31 .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
    }}
    """

    r = requests.get(WIKIDATA_SPARQL, params={
        'query': query,
        'format': 'json'
    }, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

    if r.status_code != 200:
        print(f"  Error querying Wikidata: {r.status_code}", flush=True)
        continue

    # Check if any P31 values match our classifications
    data = r.json()
    categories_to_add = []

    for binding in data['results']['bindings']:
        p31_qid = binding['p31']['value'].split('/')[-1]
        p31_label = binding['p31Label']['value']

        if p31_qid in all_p31_classifications:
            categories_to_add.append(p31_label)
            print(f"  Found: {p31_label}", flush=True)

    # Add categories if any found
    if categories_to_add:
        for cat in categories_to_add:
            category_tag = f"[[Category:{cat}]]"
            if not text.endswith('\n'):
                text += '\n'
            text += category_tag + '\n'

        # Save page
        category_list = ', '.join(categories_to_add)
        summary = f"Adding categories based on Wikidata P31: {category_list}"
        try:
            page.save(text, summary=summary)
            edit_count += 1
            print(f"  ✓ Saved! (Edit #{edit_count})", flush=True)
        except Exception as e:
            print(f"  ✗ Error saving: {e}", flush=True)
            if "429" in str(e):
                print(f"  Rate limited, waiting 60 seconds...", flush=True)
                time.sleep(60)

        time.sleep(2)  # Rate limiting - increased from 1.5 to 2
    else:
        print(f"  No matching P31 values", flush=True)

    time.sleep(1)  # Be nice to Wikidata - increased from 0.5 to 1

print(f"\n\nDone! Processed {page_count} pages, made {edit_count} edits.", flush=True)
