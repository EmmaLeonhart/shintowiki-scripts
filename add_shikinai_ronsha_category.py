#!/usr/bin/env python3
"""
Walk through mainspace, check wikidata links for P31 Q135022904 (Shikinai Ronsha),
and add [[Category:Shikinai Ronsha]] if matched.
"""

import mwclient
import requests
import time
import re
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
SHIKINAI_RONSHA_QID = "Q135022904"

print("="*70, flush=True)
print("ADD SHIKINAI RONSHA CATEGORY", flush=True)
print("="*70, flush=True)
print(flush=True)

print("Fetching all mainspace pages...", flush=True)

# Get all pages in mainspace
all_pages = site.allpages(namespace=0)

edit_count = 0
page_count = 0
checked_count = 0
matched_count = 0

for page in all_pages:
    page_count += 1
    print(f"\n[{page_count}] {page.name}", flush=True)

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

    # Look for {{wikidata link|QID}}
    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)

    if not match:
        print(f"  No wikidata link, skipping", flush=True)
        continue

    qid = match.group(1)
    print(f"  QID: {qid}", flush=True)
    checked_count += 1

    # Query Wikidata for P31 values
    query = f"""
    SELECT ?p31 WHERE {{
      wd:{qid} wdt:P31 ?p31 .
    }}
    """

    try:
        r = requests.get(WIKIDATA_SPARQL, params={
            'query': query,
            'format': 'json'
        }, headers={'User-Agent': 'WikidataBot/1.0 (https://shinto.miraheze.org/; immanuelleproject@gmail.com)'})

        if r.status_code != 200:
            print(f"  Error querying Wikidata: {r.status_code}", flush=True)
            continue

        # Check if any P31 values match Shikinai Ronsha
        data = r.json()
        is_shikinai_ronsha = False

        for binding in data['results']['bindings']:
            p31_qid = binding['p31']['value'].split('/')[-1]
            if p31_qid == SHIKINAI_RONSHA_QID:
                is_shikinai_ronsha = True
                break

        if is_shikinai_ronsha:
            matched_count += 1
            print(f"  ✓ Is Shikinai Ronsha (P31 {SHIKINAI_RONSHA_QID})", flush=True)

            # Check if category already exists
            category_tag = "[[Category:Shikinai Ronsha]]"
            if category_tag in text:
                print(f"  Already has [[Category:Shikinai Ronsha]], skipping", flush=True)
            else:
                # Add category at the end of the page
                if not text.endswith('\n'):
                    text += '\n'
                text += category_tag + '\n'

                # Save page
                try:
                    page.save(text, summary="Adding [[Category:Shikinai Ronsha]] based on Wikidata P31 Q135022904")
                    edit_count += 1
                    print(f"  ✓ Added category! (Edit #{edit_count})", flush=True)
                except Exception as e:
                    print(f"  ✗ Error saving: {e}", flush=True)
                    if "429" in str(e):
                        print(f"  Rate limited, waiting 60 seconds...", flush=True)
                        time.sleep(60)

                time.sleep(2)  # Rate limiting
        else:
            print(f"  Not Shikinai Ronsha", flush=True)

        time.sleep(1)  # Be nice to Wikidata

    except Exception as e:
        print(f"  Error processing: {e}", flush=True)
        continue

print(f"\n{'='*70}", flush=True)
print(f"PROCESSING SUMMARY", flush=True)
print(f"{'='*70}", flush=True)
print(f"Total pages: {page_count}", flush=True)
print(f"Pages with wikidata links: {checked_count}", flush=True)
print(f"Shikinai Ronsha matches: {matched_count}", flush=True)
print(f"Categories added: {edit_count}", flush=True)
print(flush=True)
