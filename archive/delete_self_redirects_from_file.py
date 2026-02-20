#!/usr/bin/env python3
"""
delete_self_redirects_from_file.py
==================================
Reads double_redirects.txt file and deletes pages that redirect to themselves.
Format: "Source (edit) → Intermediate → Final"
Self-redirects: pages where Source == Final (case-insensitive)
"""

import mwclient
import sys
import time
import re

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ────────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
DATA_FILE = 'double_redirects.txt'
THROTTLE  = 0.5  # seconds between deletions

def parse_redirect_line(line):
    """
    Parse a line from double_redirects.txt
    Format: "Source (edit) → Intermediate → Final"
    Returns: (source_name, final_name) or (None, None) if not a valid redirect entry
    """
    line = line.strip()

    # Skip empty lines and headers
    if not line or '→' not in line or line.startswith('From here'):
        return None, None

    # Split by arrow
    parts = line.split('→')
    if len(parts) < 3:
        return None, None

    # Extract source (first part, remove "(edit)" suffix)
    source = parts[0].strip()
    source = re.sub(r'\s*\(edit\)\s*$', '', source).strip()

    # Extract final target (last part)
    final = parts[-1].strip()

    # Skip empty or invalid entries
    if not source or not final:
        return None, None

    return source, final

def load_self_redirects(filepath):
    """Load and parse self-redirects from the data file"""
    self_redirects = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                source, final = parse_redirect_line(line)

                # Check if it's a self-redirect (source == final, case-insensitive)
                if source and final and source.lower() == final.lower():
                    self_redirects.append(source)

    except FileNotFoundError:
        print(f"Error: {filepath} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)

    return self_redirects

def main():
    # Load self-redirects from file
    print(f"Loading self-redirects from {DATA_FILE}...\n")
    self_redirects = load_self_redirects(DATA_FILE)

    print(f"Found {len(self_redirects)} self-redirects to delete\n")

    if not self_redirects:
        print("No self-redirects found. Exiting.")
        sys.exit(0)

    # Login to wiki
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in.\n")

    deleted_count = 0
    not_found_count = 0
    error_count = 0

    # Delete each self-redirect
    for i, page_name in enumerate(self_redirects, 1):
        try:
            page = site.pages[page_name]

            # Check if page exists
            if not page.exists:
                print(f"{i:6d}. {page_name:70s} [doesn't exist]")
                not_found_count += 1
                continue

            # Delete the page
            page.delete(reason="v25: Deleting self-redirect from Special:DoubleRedirects")
            print(f"{i:6d}. {page_name:70s} ... ✓ deleted")
            deleted_count += 1
            time.sleep(THROTTLE)

        except Exception as e:
            print(f"{i:6d}. {page_name:70s} ... ! ERROR: {str(e)[:50]}")
            error_count += 1
            time.sleep(THROTTLE / 2)

    # Print summary
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Self-redirects found: {len(self_redirects)}")
    print(f"  Deleted: {deleted_count}")
    print(f"  Not found: {not_found_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    main()
