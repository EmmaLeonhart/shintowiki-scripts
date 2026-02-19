import mwclient
import time
import re
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

print("Fetching category pages from Category:Pages linked to Wikidata...", flush=True)

# Get all pages from Category:Pages linked to Wikidata
category = site.pages['Category:Pages linked to Wikidata']

edit_count = 0
category_count = 0

for page in category:
    if page.namespace != 14:  # Category namespace is 14
        continue

    category_count += 1
    print(f"\n[{category_count}] {page.name}", flush=True)

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

    # Extract QID from category page
    match = re.search(r'\{\{wikidata link\|([Q]\d+)\}\}', text, re.IGNORECASE)
    if not match:
        print(f"  No QID found, skipping", flush=True)
        continue

    qid = match.group(1)
    print(f"  QID: {qid}", flush=True)

    # Check if QID redirect already exists
    redirect_page = site.pages[qid]
    try:
        redirect_exists = redirect_page.exists
    except:
        redirect_exists = False

    if redirect_exists:
        print(f"  {qid} already exists, skipping", flush=True)
        continue

    # Create redirect at mainspace QID -> Category:page_name
    redirect_text = f"#REDIRECT [[{page.name}]]"
    print(f"  Creating {qid} → {page.name}", flush=True)

    try:
        redirect_page.save(redirect_text, summary=f"Creating QID redirect to [[{page.name}]]")
        edit_count += 1
        print(f"  ✓ Created! (Edit #{edit_count})", flush=True)
    except Exception as e:
        print(f"  ✗ Error creating: {e}", flush=True)
        if "429" in str(e):
            print(f"  Rate limited, waiting 60 seconds...", flush=True)
            time.sleep(60)

    time.sleep(2)  # Rate limiting

print(f"\n\nDone! Processed {category_count} categories, created {edit_count} QID redirects.", flush=True)
