import mwclient
import time
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

# Get all pages from Category:Pages to be deleted
print("Fetching pages from Category:Pages to be deleted...", flush=True)
category = site.pages['Category:Pages to be deleted']
pages_to_delete = []

for page in category:
    pages_to_delete.append(page)
    print(f"  Found: {page.name}", flush=True)

print(f"\nTotal pages to delete: {len(pages_to_delete)}", flush=True)

if len(pages_to_delete) == 0:
    print("No pages to delete!", flush=True)
    exit()

# Delete pages
deleted_count = 0
for page in pages_to_delete:
    try:
        print(f"\nDeleting: {page.name}", flush=True)
        page.delete(reason="Deleting page (member of [[Category:Pages to be deleted]])")
        deleted_count += 1
        print(f"  ✓ Deleted ({deleted_count}/{len(pages_to_delete)})", flush=True)
        time.sleep(2)  # Rate limiting
    except Exception as e:
        print(f"  ✗ Error: {e}", flush=True)
        if "429" in str(e):
            print(f"  Rate limited, waiting 60 seconds...", flush=True)
            time.sleep(60)

print(f"\nDone! Deleted {deleted_count} pages.", flush=True)
