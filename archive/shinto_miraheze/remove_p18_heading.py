#!/usr/bin/env python3
"""remove_p18_heading.py
========================
Removes the "== image (P18) ==" heading and all its content from pages
in [[Category:Wikidata generated shikinaisha pages]]
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

def remove_p18_heading(text):
    """Remove == image (P18) == heading and all its content until the next heading"""
    # Match the P18 heading and everything until the next heading (or end of file)
    pattern = r'== [Ii]mage \(P18\) ==\n(?:.*?\n)*?(?===|$)'
    text = re.sub(pattern, '', text)
    return text

def main():
    print("Removing P18 (image) headings from shikinaisha pages\n")
    print("=" * 60)

    category = site.pages['Category:Wikidata generated shikinaisha pages']
    members = list(category.members())
    members = [m for m in members if m.namespace == 0]

    print(f"Found {len(members)} mainspace pages\n")

    modified_count = 0
    error_count = 0
    no_p18_count = 0

    for i, page in enumerate(members, 1):
        page_name = page.name

        try:
            page_text = page.text()
        except Exception as e:
            print(f"{i:4d}. {page_name:50s} [ERROR reading: {str(e)[:40]}]")
            error_count += 1
            continue

        # Check if page has P18 heading
        if '== image (P18) ==' not in page_text and '== Image (P18) ==' not in page_text:
            no_p18_count += 1
            continue

        # Remove P18 heading
        new_text = remove_p18_heading(page_text)

        if new_text != page_text:
            try:
                page.edit(new_text, summary="Remove P18 (image) heading - images already in infobox")
                print(f"{i:4d}. {page_name:50s} ✓ Removed P18 heading")
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
    print(f"  Modified: {modified_count}")
    print(f"  No P18 heading: {no_p18_count}")
    print(f"  Errors: {error_count}")

if __name__ == "__main__":
    main()
