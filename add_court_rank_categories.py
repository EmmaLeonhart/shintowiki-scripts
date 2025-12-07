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

# First, get all court ranks from Wikidata (we already have this from earlier)
with open('court_ranks_mapping.json', 'r', encoding='utf-8') as f:
    court_ranks = json.load(f)

print(f"Loaded {len(court_ranks)} court ranks")

# Get all pages from Category:Pages linked to Wikidata
print("\nFetching pages from Category:Pages linked to Wikidata...")
category = site.pages['Category:Pages linked to Wikidata']
pages_to_check = []

for page in category:
    if page.namespace == 0:  # Main namespace only
        pages_to_check.append(page)

print(f"Found {len(pages_to_check)} pages to check")

# Extract QIDs from pages
qid_to_page = {}
print("\nExtracting QIDs from pages...")

for page in pages_to_check:
    text = page.text()
    # Look for {{wikidata link|QID}}
    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)
    if match:
        qid = match.group(1)
        qid_to_page[qid] = page
        print(f"  {page.name}: {qid}")
    else:
        print(f"  {page.name}: No QID found")

print(f"\nFound {len(qid_to_page)} pages with QIDs")

# Query Wikidata for P31 values of these QIDs in batches
qid_list = list(qid_to_page.keys())
if not qid_list:
    print("No QIDs to check!")
    exit()

qid_to_court_ranks = {}
batch_size = 50

print(f"\nQuerying Wikidata for P31 values in batches of {batch_size}...")
for i in range(0, len(qid_list), batch_size):
    batch = qid_list[i:i+batch_size]
    print(f"  Batch {i//batch_size + 1}/{(len(qid_list)-1)//batch_size + 1} ({len(batch)} items)...")

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

        # Check if this P31 is a court rank
        if p31_qid in court_ranks:
            if item_qid not in qid_to_court_ranks:
                qid_to_court_ranks[item_qid] = []
            qid_to_court_ranks[item_qid].append({
                'qid': p31_qid,
                'label': p31_label
            })

    time.sleep(1)  # Be nice to Wikidata

print(f"\nFound {len(qid_to_court_ranks)} items with court ranks")

# Add categories to pages
for qid, ranks in qid_to_court_ranks.items():
    page = qid_to_page[qid]
    print(f"\n{page.name} ({qid}):")

    for rank in ranks:
        category_name = rank['label']
        print(f"  Adding [[Category:{category_name}]]")

        text = page.text()
        category_tag = f"[[Category:{category_name}]]"

        # Check if category already exists
        if category_tag in text:
            print(f"    Already has category, skipping")
            continue

        # Add category at the end of the page
        if not text.endswith('\n'):
            text += '\n'
        text += category_tag + '\n'

        # Save page
        page.save(text, summary=f"Adding [[Category:{category_name}]] based on Wikidata P31 value")
        print(f"    ✓ Added")
        time.sleep(1.5)  # Rate limiting

print("\nDone!")
