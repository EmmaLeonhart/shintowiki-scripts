#!/usr/bin/env python3
"""
create_blank_shikinaisha_placeholders.py
========================================
Create placeholder pages for all pages in
[[Category:Blank Shikinaisha with no wikidata]]

Adds pages with content:
    '''Page Name''' is a {{nihongo|Shikinaisha|式內社}} or a shrine in the
    {{ill|Engishiki Jinmyōchō|zh|延喜式神名帳|ja|延喜式神名帳}}.
    [[Category:Placeholder Shikinaisha pages]]
"""

import mwclient
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'
CATEGORY  = 'Blank Shikinaisha with no wikidata'
SLEEP     = 1.5  # seconds between edits

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

print("Logged in\n")

# ─── HELPERS ─────────────────────────────────────────────────

def create_placeholder_content(page_name):
    """Create placeholder content for a Shikinaisha page."""
    return f"""'''{page_name}''' is a {{{{nihongo|Shikinaisha|式內社}}}} or a shrine in the {{{{ill|Engishiki Jinmyōchō|zh|延喜式神名帳|ja|延喜式神名帳}}}}. [[Category:Placeholder Shikinaisha pages]]"""

# ─── MAIN LOOP ───────────────────────────────────────────────

cat = site.pages[f'Category:{CATEGORY}']

if not cat.exists:
    print(f"[ERROR] Category '{CATEGORY}' does not exist")
    sys.exit(1)

print(f"[INFO] Creating placeholder pages for all pages in Category:{CATEGORY}\n")

pages = list(cat)
print(f"[INFO] Found {len(pages)} pages to process\n")

success_count = 0
fail_count = 0

for pg in pages:
    # Only process main namespace
    if pg.namespace != 0:
        print(f"[SKIP] {pg.name} (not in main namespace)")
        continue

    try:
        page_name = pg.name
        print(f"Processing: {page_name}")

        # Create the placeholder content
        content = create_placeholder_content(page_name)

        # Save the page
        pg.save(content, summary='Bot: Create placeholder Shikinaisha page')
        print(f"  [DONE] placeholder created")
        success_count += 1

    except Exception as e:
        print(f"  [FAILED] {e}")
        fail_count += 1

    time.sleep(SLEEP)

print(f"\n[SUMMARY] {success_count} created, {fail_count} failed")
