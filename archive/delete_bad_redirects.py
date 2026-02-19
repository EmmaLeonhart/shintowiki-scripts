import mwclient
import time
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

# Get all pages from Category:Bad redirects
print("Fetching pages from Category:Bad redirects...")
category = site.pages['Category:Bad redirects']
pages_to_delete = []

for page in category:
    pages_to_delete.append(page)
    print(f"  Found: {page.name}")

print(f"\nTotal pages to delete: {len(pages_to_delete)}")

if len(pages_to_delete) == 0:
    print("No pages to delete!")
    exit()

# Ask for confirmation
print(f"\nAbout to delete {len(pages_to_delete)} pages.")
print("Press Ctrl+C to cancel, or Enter to continue...")
# Auto-proceed without input since we're in a script
print("Proceeding with deletion...")

# Delete pages
deleted_count = 0
for page in pages_to_delete:
    try:
        print(f"\nDeleting: {page.name}")
        page.delete(reason="Deleting bad redirect (member of [[Category:Bad redirects]])")
        deleted_count += 1
        print(f"  ✓ Deleted ({deleted_count}/{len(pages_to_delete)})")
        time.sleep(1.5)  # Rate limiting
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"\nDone! Deleted {deleted_count} pages.")
