"""log_wikidata_links.py
================================================
Log all Wikidata QIDs linked from [[Category:Pages linked to Wikidata]]
and identify duplicates
================================================

This script:
1. Walks through [[Category:Pages linked to Wikidata]]
2. Extracts the Wikidata QID from each page
3. Logs all QIDs with their page names
4. Identifies and reports duplicate QIDs
5. Writes results to a text file
"""

import mwclient
import sys
import re
from collections import defaultdict

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    # Try to find {{wikidata link|Q...}}
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Try to find [[wikidata:Q...]]
    match = re.search(r'\[\[wikidata:([Qq](\d+))\]\]', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def main():
    """Log all Wikidata QIDs from [[Category:Pages linked to Wikidata]]."""

    print("Logging Wikidata QIDs from category\n")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Pages linked to Wikidata']

    print(f"\nFetching all pages in [[Category:Pages linked to Wikidata]]...")
    try:
        members = list(category.members())
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} pages\n")

    # Data structures
    qid_to_pages = defaultdict(list)  # Maps QID to list of pages
    pages_with_qids = []  # List of (page_name, qid) tuples
    pages_without_qids = []  # List of pages without QIDs

    # Process all pages
    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end=" ... ")

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)

            if qid:
                print(f"✓ {qid}")
                pages_with_qids.append((page_name, qid))
                qid_to_pages[qid].append(page_name)
            else:
                print(f"• No QID")
                pages_without_qids.append(page_name)

        except Exception as e:
            try:
                print(f"! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"! ERROR: {str(e)}")
            pages_without_qids.append(page.name if 'page' in locals() else '[unknown]')

    # Find duplicates
    duplicates = {qid: pages for qid, pages in qid_to_pages.items() if len(pages) > 1}

    # Write to file
    output_filename = 'wikidata_links_log.txt'
    print(f"\n{'=' * 60}")
    print(f"\nWriting results to {output_filename}...\n")

    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 70 + "\n")
            f.write("WIKIDATA LINKS LOG FROM [[Category:Pages linked to Wikidata]]\n")
            f.write("=" * 70 + "\n\n")

            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total pages in category: {len(members)}\n")
            f.write(f"Pages with Wikidata links: {len(pages_with_qids)}\n")
            f.write(f"Pages without Wikidata links: {len(pages_without_qids)}\n")
            f.write(f"Unique Wikidata QIDs: {len(qid_to_pages)}\n")
            f.write(f"Duplicate QIDs (linked from multiple pages): {len(duplicates)}\n\n")

            # All pages with their QIDs
            f.write("=" * 70 + "\n")
            f.write("ALL PAGES WITH WIKIDATA LINKS\n")
            f.write("=" * 70 + "\n\n")

            for page_name, qid in sorted(pages_with_qids):
                f.write(f"{page_name:50s} → {qid}\n")

            # Pages without QIDs
            if pages_without_qids:
                f.write("\n" + "=" * 70 + "\n")
                f.write("PAGES WITHOUT WIKIDATA LINKS\n")
                f.write("=" * 70 + "\n\n")

                for page_name in sorted(pages_without_qids):
                    f.write(f"• {page_name}\n")

            # Duplicate QIDs
            if duplicates:
                f.write("\n" + "=" * 70 + "\n")
                f.write("DUPLICATE WIKIDATA ITEMS (linked from multiple pages)\n")
                f.write("=" * 70 + "\n\n")

                for qid in sorted(duplicates.keys()):
                    pages = duplicates[qid]
                    f.write(f"\n{qid} (linked from {len(pages)} pages):\n")
                    for page_name in sorted(pages):
                        f.write(f"  • {page_name}\n")

            # QID frequency analysis
            f.write("\n" + "=" * 70 + "\n")
            f.write("WIKIDATA QID FREQUENCY ANALYSIS\n")
            f.write("=" * 70 + "\n\n")

            # Sort by frequency
            qid_counts = sorted(qid_to_pages.items(), key=lambda x: len(x[1]), reverse=True)
            for qid, pages in qid_counts:
                count = len(pages)
                marker = "⚠ DUPLICATE" if count > 1 else "✓ unique"
                f.write(f"{qid:10s} - {count:3d} page(s) [{marker}]\n")
                if count <= 3:  # Show pages for low-frequency QIDs
                    for page_name in sorted(pages):
                        f.write(f"           - {page_name}\n")

        print(f"✓ Log file created: {output_filename}")

        # Print summary to console
        print(f"\nSummary:")
        print(f"  Total pages: {len(members)}")
        print(f"  With QIDs: {len(pages_with_qids)}")
        print(f"  Without QIDs: {len(pages_without_qids)}")
        print(f"  Unique QIDs: {len(qid_to_pages)}")
        print(f"  Duplicate QIDs: {len(duplicates)}")

        if duplicates:
            print(f"\n  Duplicates found:")
            for qid in sorted(duplicates.keys()):
                print(f"    - {qid}: {len(duplicates[qid])} pages")

    except Exception as e:
        print(f"! Error writing to file: {e}")


if __name__ == "__main__":
    main()
