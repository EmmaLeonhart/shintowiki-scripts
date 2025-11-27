"""export_translated_missing_wikidata.py
================================================
Export pages from [[Category:Translated page but missing wikidata]]
as CSV with local title and jawiki interwiki link.
================================================

This script:
1. Gets all pages in [[Category:Translated page but missing wikidata]]
2. Extracts the jawiki interwiki link from each page
3. Exports as CSV: local_title,jawiki_interwiki
"""

import mwclient
import re
import sys
import csv

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")


# ─── REGEX PATTERNS ─────────────────────────────────────────

# Match interwiki links like [[ja:XX]], [[en:YY]], etc.
INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')


# ─── HELPERS ─────────────────────────────────────────────────

def extract_jawiki_link(text):
    """Extract the jawiki interwiki link from page text.
    Returns the full interwiki link (e.g., "ja:Page Title") or None if not found.
    """
    matches = INTERWIKI_RE.findall(text)
    for lang, title in matches:
        if lang == 'ja':
            return f"{lang}:{title}"
    return None


def main():
    """Export pages to CSV."""

    print("Fetching pages from [[Category:Translated page but missing wikidata]]...\n")

    try:
        # Get the category page
        category = site.pages['Category:Translated page but missing wikidata']
        pages = list(category)
    except Exception as e:
        print(f"ERROR: Could not fetch category – {e}")
        return

    if not pages:
        print("No pages found in category")
        return

    print(f"Found {len(pages)} pages\n")

    # Collect results
    results = []
    processed = 0
    with_jawiki = 0

    for idx, page in enumerate(pages, 1):
        try:
            page_title = page.name

            try:
                text = page.text()
            except Exception as e:
                print(f"{idx}. [[{page_title}]] – ERROR reading: {e}")
                continue

            # Extract jawiki link
            jawiki_link = extract_jawiki_link(text)

            if jawiki_link:
                results.append((page_title, jawiki_link))
                with_jawiki += 1
                print(f"{idx}. [[{page_title}]] → {jawiki_link}")
            else:
                print(f"{idx}. [[{page_title}]] – no jawiki link found")

            processed += 1

        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

    # Write CSV
    csv_filename = "translated_missing_wikidata.csv"
    print(f"\n\nWriting {len(results)} results to {csv_filename}...")

    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Local Title', 'Jawiki Interwiki'])
            writer.writerows(results)
        print(f"Done! Exported {len(results)} pages to {csv_filename}")
    except Exception as e:
        print(f"ERROR writing CSV: {e}")

    print(f"\nSummary:")
    print(f"  Total pages processed: {processed}")
    print(f"  Pages with jawiki link: {with_jawiki}")
    print(f"  Pages without jawiki link: {processed - with_jawiki}")


if __name__ == "__main__":
    main()
