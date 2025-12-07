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

print("Fetching all mainspace pages...", flush=True)

# Get all pages in mainspace
all_pages = site.allpages(namespace=0)

edit_count = 0
page_count = 0
skipped_redirect_count = 0

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

    # Skip redirects (pages that start with #)
    if text.strip().startswith('#'):
        skipped_redirect_count += 1
        print(f"  SKIPPING (redirect)", flush=True)
        continue

    # Check if page has {{translated page|...}} template
    has_translated_template = bool(re.search(r'\{\{translated page\|', text, re.IGNORECASE))

    # Check if page has [[Category:Wikidata generated shikinaisha pages]]
    has_wikidata_shikinaisha = '[[Category:Wikidata generated shikinaisha pages]]' in text

    # Check if already has the target category
    has_no_translation_category = '[[Category:Pages without translation templates]]' in text

    if has_translated_template:
        print(f"  Has {{{{translated page}}}} template", flush=True)

    if has_wikidata_shikinaisha:
        print(f"  Has [[Category:Wikidata generated shikinaisha pages]]", flush=True)

    # If has neither, add category
    if not has_translated_template and not has_wikidata_shikinaisha:
        if has_no_translation_category:
            print(f"  Already has [[Category:Pages without translation templates]]", flush=True)
        else:
            print(f"  Adding [[Category:Pages without translation templates]]", flush=True)

            if not text.endswith('\n'):
                text += '\n'
            text += '[[Category:Pages without translation templates]]\n'

            try:
                page.save(text, summary="Adding [[Category:Pages without translation templates]]")
                edit_count += 1
                print(f"  ✓ Saved! (Edit #{edit_count})", flush=True)
            except Exception as e:
                print(f"  ✗ Error saving: {e}", flush=True)
                if "429" in str(e):
                    print(f"  Rate limited, waiting 60 seconds...", flush=True)
                    time.sleep(60)

            time.sleep(2)  # Rate limiting

print(f"\n\nDone! Processed {page_count} pages, skipped {skipped_redirect_count} redirects, made {edit_count} edits.", flush=True)
