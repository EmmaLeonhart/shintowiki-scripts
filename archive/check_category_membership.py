import mwclient
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to shinto.miraheze.org
site = mwclient.Site('shinto.miraheze.org')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

# Check if Folk Cultural Property is in the category
category = site.pages['Category:Pages without translation templates']
print("Checking if 'Folk Cultural Property' is in [[Category:Pages without translation templates]]...", flush=True)

found = False
for page in category:
    if page.name == 'Folk Cultural Property':
        found = True
        print(f"YES - Found in category!", flush=True)
        break

if not found:
    print("NO - Not found in category", flush=True)

# Also check what categories Folk Cultural Property has
page = site.pages['Folk Cultural Property']
print(f"\nCategories on 'Folk Cultural Property':", flush=True)
for cat in page.categories():
    print(f"  {cat.name}", flush=True)
