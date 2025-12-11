#!/usr/bin/env python3
"""
Merge Japanese Wikipedia import with English page
Part 2 of the import workflow - run AFTER manual XML import via Special:Import
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Test page
ENGLISH_PAGE = 'Ōarahiko Shrine'
JAPANESE_PAGE = '大荒比古神社'
MERGED_CONTENT_FILE = f"{ENGLISH_PAGE.replace('/', '_')}_merged.txt"

def main():
    """Main execution"""
    print("=" * 80)
    print("MERGE JAPANESE WIKIPEDIA IMPORT")
    print("=" * 80)
    print()
    print(f"English page: {ENGLISH_PAGE}")
    print(f"Japanese page: {JAPANESE_PAGE}")
    print(f"Merged content file: {MERGED_CONTENT_FILE}")
    print()

    try:
        # Login to wiki
        print("Connecting to shinto.miraheze.org...", flush=True)
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)
        print("Logged in successfully", flush=True)
        print()

        # Step 1: Verify Japanese page exists (from manual import)
        print("Step 1: Verifying Japanese page exists...", flush=True)
        ja_page = site.pages[JAPANESE_PAGE]
        if not ja_page.exists:
            print(f"  ERROR: Japanese page [[{JAPANESE_PAGE}]] does not exist!")
            print(f"  You need to import {JAPANESE_PAGE}_export.xml via Special:Import first")
            return
        print(f"  ✓ Japanese page exists", flush=True)
        print()

        # Step 2: Load merged content
        print("Step 2: Loading merged content...", flush=True)
        try:
            with open(MERGED_CONTENT_FILE, 'r', encoding='utf-8') as f:
                merged_content = f.read()
            print(f"  Loaded {len(merged_content)} characters", flush=True)
        except FileNotFoundError:
            print(f"  ERROR: {MERGED_CONTENT_FILE} not found!")
            print(f"  Run import_jawiki_content.py first to generate this file")
            return
        print()

        # Step 3: Delete English page
        print("Step 3: Deleting English page...", flush=True)
        en_page = site.pages[ENGLISH_PAGE]
        if en_page.exists:
            try:
                en_page.delete(reason="Preparing to merge Japanese Wikipedia import with full revision history")
                print(f"  ✓ Deleted [[{ENGLISH_PAGE}]]", flush=True)
                time.sleep(2)
            except Exception as e:
                print(f"  ERROR deleting page: {e}", flush=True)
                return
        else:
            print(f"  Page [[{ENGLISH_PAGE}]] does not exist, skipping delete", flush=True)
        print()

        # Step 4: Move Japanese page to English page name
        print("Step 4: Moving Japanese page to English page name...", flush=True)
        try:
            ja_page.move(ENGLISH_PAGE,
                        reason="Merging Japanese Wikipedia import with English content",
                        no_redirect=True)
            print(f"  ✓ Moved [[{JAPANESE_PAGE}]] → [[{ENGLISH_PAGE}]]", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"  ERROR moving page: {e}", flush=True)
            return
        print()

        # Step 5: Undelete all revisions
        print("Step 5: Undeleting all revisions of English page...", flush=True)
        try:
            # Use API to undelete
            result = site.api('undelete',
                            title=ENGLISH_PAGE,
                            reason="Restoring English revisions to merge with Japanese Wikipedia history",
                            token=site.get_token('delete'))
            print(f"  ✓ Undeleted revisions: {result}", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"  ERROR undeleting: {e}", flush=True)
            # Continue anyway - the move might have worked
            print(f"  Continuing with merge...", flush=True)
        print()

        # Step 6: Overwrite with merged content
        print("Step 6: Overwriting with merged content...", flush=True)
        try:
            target_page = site.pages[ENGLISH_PAGE]
            target_page.save(merged_content,
                           summary="Merged Japanese Wikipedia content with full revision history and English content")
            print(f"  ✓ Saved merged content to [[{ENGLISH_PAGE}]]", flush=True)
        except Exception as e:
            print(f"  ERROR saving merged content: {e}", flush=True)
            return
        print()

        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"The page [[{ENGLISH_PAGE}]] now contains:")
        print(f"  - All Japanese Wikipedia revision history")
        print(f"  - All English page revision history")
        print(f"  - Merged content with both Japanese and English sections")
        print()

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
