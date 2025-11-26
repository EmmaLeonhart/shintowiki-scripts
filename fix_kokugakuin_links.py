#!/usr/bin/env python3
"""fix_kokugakuin_links.py
=========================
Fixes Kokugakuin University Digital Museum entry IDs (P13677) by converting
bare IDs like "182421" into proper links like
[https://jmapps.ne.jp/kokugakuin/det.html?data_id=182421 shrine database]
"""

import mwclient
import sys
import time
import re

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API)\n")

def fix_kokugakuin_ids(text):
    """
    Find P13677 headings and convert bare IDs into proper links.
    Matches pattern like:
    == Kokugakuin University Digital Museum entry ID (P13677) ==
    * 182421
    ** P3831: ...

    And converts to:
    == Kokugakuin University Digital Museum entry ID (P13677) ==
    * [https://jmapps.ne.jp/kokugakuin/det.html?data_id=182421 shrine database]
    ** P3831: ...
    """

    # Pattern to find P13677 sections with bare numeric IDs
    # Matches: == ... (P13677) == followed by * and a bare number
    pattern = r'(== [^\n]*\(P13677\)[^\n]* ==\n)\* (\d+)\n'

    def replace_id(match):
        heading = match.group(1)
        data_id = match.group(2)
        url = f"[https://jmapps.ne.jp/kokugakuin/det.html?data_id={data_id} shrine database]"
        return f"{heading}* {url}\n"

    text = re.sub(pattern, replace_id, text)
    return text

def main():
    print("Fixing Kokugakuin University Digital Museum links\n")
    print("=" * 60)

    category = site.pages['Category:Wikidata generated shikinaisha pages']
    members = list(category.members())
    members = [m for m in members if m.namespace == 0]

    print(f"Found {len(members)} mainspace pages\n")

    modified_count = 0
    error_count = 0
    no_p13677_count = 0

    for i, page in enumerate(members, 1):
        page_name = page.name

        try:
            page_text = page.text()
        except Exception as e:
            print(f"{i:4d}. {page_name:50s} [ERROR reading: {str(e)[:40]}]")
            error_count += 1
            continue

        # Check if page has P13677 heading
        if '(P13677)' not in page_text:
            no_p13677_count += 1
            continue

        # Fix P13677 IDs
        new_text = fix_kokugakuin_ids(page_text)

        if new_text != page_text:
            try:
                page.edit(new_text, summary="Fix Kokugakuin University Digital Museum entry IDs with proper links")
                print(f"{i:4d}. {page_name:50s} ✓ Fixed Kokugakuin links")
                modified_count += 1

                # Rate limiting
                time.sleep(1.5)

            except Exception as e:
                print(f"{i:4d}. {page_name:50s} [ERROR saving: {str(e)[:40]}]")
                error_count += 1
                time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Fixed: {modified_count}")
    print(f"  No P13677 heading: {no_p13677_count}")
    print(f"  Errors: {error_count}")

if __name__ == "__main__":
    main()
