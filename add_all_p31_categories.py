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
print(f"  - Court ranks: {len(court_ranks)}", flush=True)
print(f"  - Shrine classifications: {len(shrine_classifications)}", flush=True)

# Get all pages from Category:Pages linked to Wikidata
print("\nFetching pages from Category:Pages linked to Wikidata...", flush=True)
category = site.pages['Category:Pages linked to Wikidata']
pages_to_check = []

for page in category:
    if page.namespace == 0:  # Main namespace only
        pages_to_check.append(page)

print(f"Found {len(pages_to_check)} pages to check", flush=True)

# Extract QIDs from pages
qid_to_page = {}
print("\nExtracting QIDs from pages...", flush=True)

for i, page in enumerate(pages_to_check):
    if i % 100 == 0:
        print(f"  Processed {i}/{len(pages_to_check)} pages...", flush=True)

    text = page.text()
    # Look for {{wikidata link|QID}}
    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)
    if match:
        qid = match.group(1)
        qid_to_page[qid] = page

print(f"\nFound {len(qid_to_page)} pages with QIDs", flush=True)

# Query Wikidata for P31 values of these QIDs in batches
qid_list = list(qid_to_page.keys())
if not qid_list:
    print("No QIDs to check!")
    exit()

qid_to_p31_classifications = {}
batch_size = 50

print(f"\nQuerying Wikidata for P31 values in batches of {batch_size}...", flush=True)
for i in range(0, len(qid_list), batch_size):
    batch = qid_list[i:i+batch_size]
    print(f"  Batch {i//batch_size + 1}/{(len(qid_list)-1)//batch_size + 1} ({len(batch)} items)...", flush=True)

    # Build SPARQL query
    values_clause = ' '.join([f'wd:{qid}' for qid in batch])
    query = f"""
    SELECT ?item ?p31 ?p31Label WHERE {{
      VALUES ?item {{ {values_clause} }}
      ?item wdt:P31 ?p31 .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
    }}
    """

    r = requests.get(WIKIDATA_SPARQL, params={
        'query': query,
        'format': 'json'
    }, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        print(r.text)
        continue

    # Process results
    data = r.json()
    for binding in data['results']['bindings']:
        item_qid = binding['item']['value'].split('/')[-1]
        p31_qid = binding['p31']['value'].split('/')[-1]
        p31_label = binding['p31Label']['value']

        # Check if this P31 is one of our classifications
        if p31_qid in all_p31_classifications:
            if item_qid not in qid_to_p31_classifications:
                qid_to_p31_classifications[item_qid] = []
            qid_to_p31_classifications[item_qid].append({
                'qid': p31_qid,
                'label': p31_label
            })

    time.sleep(1)  # Be nice to Wikidata

print(f"\nFound {len(qid_to_p31_classifications)} items with P31 classifications", flush=True)

# Add categories to pages
edit_count = 0
for qid, classifications in qid_to_p31_classifications.items():
    page = qid_to_page[qid]
    print(f"\n{page.name} ({qid}):", flush=True)

    text = page.text()

    for classification in classifications:
        category_name = classification['label']
        print(f"  Adding [[Category:{category_name}]]", flush=True)

        category_tag = f"[[Category:{category_name}]]"

        # Add category at the end of the page (even if it exists - for evidence)
        if not text.endswith('\n'):
            text += '\n'
        text += category_tag + '\n'

    # Save page
    category_list = ', '.join([c['label'] for c in classifications])
    summary = f"Adding categories based on Wikidata P31: {category_list}"
    page.save(text, summary=summary)
    edit_count += 1
    print(f"    ✓ Saved! (Edit #{edit_count})", flush=True)
    time.sleep(1.5)  # Rate limiting

print(f"\nDone! Made {edit_count} edits.", flush=True)
