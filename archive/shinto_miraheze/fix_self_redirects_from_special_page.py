#!/usr/bin/env python3
"""
fix_self_redirects_from_special_page.py
======================================
Gets all double redirects from Special:DoubleRedirects and deletes source pages
that redirect to themselves.
"""

import re
import sys
import time

import mwclient

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
THROTTLE  = 0.5

def get_redirect_target(page_text):
    """Extract the target of a #redirect statement"""
    match = re.search(r'#redirect\s*\[\[\s*([^\]]+)\]\]', page_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in.\n")

    # Get all pages from Special:DoubleRedirects
    print("Fetching double redirects from Special:DoubleRedirects...")
    try:
        special_page = site.pages['Special:DoubleRedirects']
        # Get all links that appear in the special page
        double_redirect_pages = list(special_page.links())
    except Exception as e:
        print(f"Error fetching Special:DoubleRedirects: {e}")
        sys.exit(1)

    print(f"Found {len(double_redirect_pages)} pages in double redirects list\n")

    sources_to_delete = []

    # Check each page to see if it's a self-redirect
    for i, page in enumerate(double_redirect_pages, 1):
        page_name = page.name

        try:
            text = page.text()
            target = get_redirect_target(text)

            if not target:
                # Not a redirect, skip
                continue

            # Check if target redirects back to source (self-redirect)
            try:
                target_page = site.pages[target]
                target_text = target_page.text()
                target_target = get_redirect_target(target_text)

                if target_target and target_target.lower() == page_name.lower():
                    # Self-redirect found!
                    sources_to_delete.append(page_name)
                    if i % 50 == 0:
                        print(f"[{i}/{len(double_redirect_pages)}] Found self-redirect: {page_name} → {target} → {page_name}", flush=True)
            except:
                # Can't check target, skip
                pass

        except Exception as e:
            if i % 100 == 0:
                print(f"[{i}/{len(double_redirect_pages)}] Error checking {page_name}: {str(e)[:50]}", flush=True)

    print(f"\nFound {len(sources_to_delete)} self-redirects to delete\n")

    deleted_count = 0
    error_count = 0

    for i, source_name in enumerate(sources_to_delete, 1):
        try:
            page = site.pages[source_name]
            print(f"{i:6d}. {source_name:70s} ... ", end='', flush=True)

            if not page.exists:
                print("(doesn't exist)")
                continue

            page.delete(reason="v25: Deleting self-redirect from Special:DoubleRedirects")
            print("✓ deleted")
            deleted_count += 1
            time.sleep(THROTTLE)

        except Exception as e:
            print(f"! ERROR: {str(e)[:50]}")
            error_count += 1
            time.sleep(THROTTLE / 2)

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Pages in double redirects list: {len(double_redirect_pages)}")
    print(f"  Self-redirects found: {len(sources_to_delete)}")
    print(f"  Deleted: {deleted_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    main()
