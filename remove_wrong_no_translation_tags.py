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

print("Fetching pages from Category:Pages without translation templates...", flush=True)

# Get all pages from the category
category = site.pages['Category:Pages without translation templates']

edit_count = 0
page_count = 0
skipped_count = 0

for page in category:
    if page.namespace != 0:  # Main namespace only
        continue

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

    # Check if page actually HAS the template now
    has_translated_template = bool(re.search(r'\{\{translated page\|', text, re.IGNORECASE))

    if has_translated_template:
        print(f"  Page HAS {{{{translated page}}}} template, removing wrong category tag", flush=True)

        # Remove the category
        new_text = text.replace('[[Category:Pages without translation templates]]\n', '')
        new_text = new_text.replace('[[Category:Pages without translation templates]]', '')

        if new_text != text:
            try:
                page.save(new_text, summary="Removing [[Category:Pages without translation templates]] - page now has {{translated page}} template")
                edit_count += 1
                print(f"  ✓ Removed category! (Edit #{edit_count})", flush=True)
            except Exception as e:
                print(f"  ✗ Error saving: {e}", flush=True)
                if "429" in str(e):
                    print(f"  Rate limited, waiting 60 seconds...", flush=True)
                    time.sleep(60)

            time.sleep(2)  # Rate limiting
        else:
            print(f"  Category not found in text (might have been removed already)", flush=True)
    else:
        print(f"  Page correctly lacks template, keeping category", flush=True)
        skipped_count += 1

    time.sleep(1)  # Rate limiting between checks

print(f"\n\nDone! Processed {page_count} pages, removed category from {edit_count} pages, kept {skipped_count} pages.", flush=True)
