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

print("Fetching all mainspace redirects...", flush=True)

# Get all redirects in mainspace
all_redirects = site.allpages(namespace=0, filterredir='redirects')

edit_count = 0
redirect_count = 0

for page in all_redirects:
    redirect_count += 1
    print(f"\n[{redirect_count}] {page.name}", flush=True)

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

    # Check if page has any categories
    has_categories = bool(re.search(r'\[\[Category:', text, re.IGNORECASE))

    if has_categories:
        print(f"  Has categories, removing them", flush=True)

        # Remove all category tags
        new_text = re.sub(r'\[\[Category:[^\]]+\]\]\n?', '', text, flags=re.IGNORECASE)

        if new_text != text:
            try:
                page.save(new_text, summary="Removing categories from redirect")
                edit_count += 1
                print(f"  ✓ Saved! (Edit #{edit_count})", flush=True)
            except Exception as e:
                print(f"  ✗ Error saving: {e}", flush=True)
                if "429" in str(e):
                    print(f"  Rate limited, waiting 60 seconds...", flush=True)
                    time.sleep(60)

            time.sleep(2)  # Rate limiting
        else:
            print(f"  No categories found in regex (might be false positive)", flush=True)
    else:
        print(f"  No categories", flush=True)

    time.sleep(1)  # Rate limiting between checks

print(f"\n\nDone! Processed {redirect_count} redirects, removed categories from {edit_count} pages.", flush=True)
