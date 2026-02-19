#!/usr/bin/env python3
"""
add_dummy_category_evolutionism.py
==================================
Adds [[Category:Pages]] to all pages across all namespaces on evolutionism.miraheze.org,
excluding Wikibase namespaces (Item, Property, Lexeme and their talk pages).
This is a dummy edit to make categories work after wiki restoration.
"""

import mwclient
import sys
import time

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKI_URL = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.5  # seconds between edits

CATEGORY_TO_ADD = "[[Category:Pages]]"
EDIT_SUMMARY = "Bot: Adding dummy category to make categories work after wiki restoration"

# Wikibase namespace names to exclude (case-insensitive check)
EXCLUDED_NS_NAMES = {'item', 'property', 'lexeme', 'item talk', 'property talk', 'lexeme talk'}

# Resume: skip mainspace pages alphabetically before this (set to None to start fresh)
RESUME_NS = 0
RESUME_FROM = "Qq"

def main():
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully\n")

    # Get all namespaces from the site
    all_namespaces = site.namespaces
    print("All namespaces on this wiki:")
    for ns_id, ns_name in sorted(all_namespaces.items()):
        print(f"  {ns_id}: {ns_name}")

    # Filter: keep only non-negative namespaces, exclude wikibase ones
    namespaces_to_process = []
    for ns_id, ns_name in sorted(all_namespaces.items()):
        if ns_id < 0:
            continue
        if ns_name.lower() in EXCLUDED_NS_NAMES:
            print(f"\n  [EXCLUDE] ns={ns_id} ({ns_name}) - Wikibase namespace")
            continue
        namespaces_to_process.append((ns_id, ns_name))

    print(f"\nWill process {len(namespaces_to_process)} namespaces:")
    for ns_id, ns_name in namespaces_to_process:
        label = ns_name if ns_name else "(Main)"
        print(f"  {ns_id}: {label}")

    total_processed = 0
    total_success = 0
    total_failed = 0
    total_skipped = 0

    for ns_id, ns_name in namespaces_to_process:
        label = ns_name if ns_name else "(Main)"
        print(f"\n{'='*60}")
        print(f"Processing namespace {ns_id}: {label}")
        print('='*60)

        # Resume support: for the resume namespace, use start parameter
        if RESUME_FROM and ns_id == RESUME_NS:
            print(f"[RESUME] Starting from '{RESUME_FROM}' in ns={ns_id}")
            pages = site.allpages(namespace=ns_id, start=RESUME_FROM)
        elif RESUME_FROM and ns_id < RESUME_NS:
            print(f"[SKIP NS] Already completed in previous run")
            continue
        else:
            pages = site.allpages(namespace=ns_id)

        ns_count = 0
        for page in pages:
            total_processed += 1
            ns_count += 1
            page_title = page.name

            try:
                content = page.text()

                if "[[Category:Pages]]" in content:
                    print(f"[SKIP] {page_title}")
                    total_skipped += 1
                    continue

                new_content = content.rstrip() + "\n" + CATEGORY_TO_ADD

                page.save(new_content, summary=EDIT_SUMMARY)
                print(f"[OK] {page_title}")
                total_success += 1

            except Exception as e:
                print(f"[FAILED] {page_title}: {e}")
                total_failed += 1

            time.sleep(SLEEP)

        print(f"  -> {ns_count} pages in this namespace")

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print('='*60)
    print(f"Total processed: {total_processed}")
    print(f"Successfully edited: {total_success}")
    print(f"Skipped (already has category): {total_skipped}")
    print(f"Failed: {total_failed}")

if __name__ == "__main__":
    main()
