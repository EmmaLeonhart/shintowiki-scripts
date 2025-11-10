"""categorize_wikidata_links.py
================================================
Check Wikidata P11250 property and categorize pages accordingly
================================================

This script:
1. Walks through [[Category:Pages linked to Wikidata]]
2. Extracts the {{wikidata link|Q12345}} from each page
3. Queries Wikidata for property P11250
4. Adds categories based on whether P11250 exists and matches the page name
   - [[Category:Pages linked to by wikidata]] if P11250 exists
   - [[Category:Matching pagename on wikidata]] if P11250 matches shinto:$PAGENAME
   - [[Category:Non matching pagename on wikidata]] if P11250 doesn't match
"""

import mwclient
import requests
import sys
import time
import re

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


def get_wikidata_p11250(qid):
    """Query Wikidata for P11250 property value."""
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        headers = {"User-Agent": "WikidataBot/1.0 (https://shinto.miraheze.org/; bot for checking wikidata links)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        entity = data.get('entities', {}).get(qid, {})

        # Look for P11250 property
        claims = entity.get('claims', {})
        p11250_claims = claims.get('P11250', [])

        if not p11250_claims:
            return None

        # Get the value of the first P11250 claim
        claim = p11250_claims[0]
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        value = datavalue.get('value', '')

        return value if value else None

    except Exception as e:
        print(f"     ! Error querying Wikidata {qid}: {e}")
        return None


def has_category(page_text, category_name):
    """Check if a page already has a category."""
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]'
    return bool(re.search(pattern, page_text, re.IGNORECASE))


def add_category(page_text, category_name):
    """Add a category to the page if it doesn't already have it."""
    if has_category(page_text, category_name):
        return page_text

    # Add category at the end
    return page_text.rstrip() + f"\n[[Category:{category_name}]]"


def remove_category(page_text, category_name):
    """Remove a category from the page."""
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]\n?'
    return re.sub(pattern, '', page_text, flags=re.IGNORECASE)


def main():
    """Process all pages in [[Category:Pages linked to Wikidata]]."""

    print("Categorizing Wikidata links based on P11250 property\n")
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

    processed_count = 0
    has_p11250_count = 0
    matching_count = 0
    non_matching_count = 0
    error_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end="")

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                print(f" ... • No QID found")
                continue

            print(f" ({qid})", end="")

            # Query Wikidata for P11250
            p11250_value = get_wikidata_p11250(qid)

            if not p11250_value:
                print(f" ... • No P11250 property")
                # Remove the "pages linked to by wikidata" category if it exists
                if has_category(text, "Pages linked to by wikidata"):
                    text = remove_category(text, "Pages linked to by wikidata")
                    try:
                        page.edit(text, summary="Bot: remove 'pages linked to by wikidata' category (no P11250)")
                        print(f" [removed category]")
                    except Exception as e:
                        print(f" ! Error saving: {e}")
                continue

            # Has P11250, add the "pages linked to by wikidata" category
            text = add_category(text, "Pages linked to by wikidata")
            has_p11250_count += 1

            # Check if P11250 matches the page name
            # Format: "shinto:PageName" or similar wiki prefix
            expected_pattern = f"shinto:{page_name.replace(' ', '_')}"

            is_matching = p11250_value == expected_pattern

            if is_matching:
                print(f" ... ✓ Matching ({p11250_value})")
                matching_count += 1
                # Add matching category
                text = add_category(text, "Matching pagename on wikidata")
                # Remove non-matching if present
                text = remove_category(text, "Non matching pagename on wikidata")
            else:
                print(f" ... ✗ Non-matching (expected: {expected_pattern}, got: {p11250_value})")
                non_matching_count += 1
                # Add non-matching category
                text = add_category(text, "Non matching pagename on wikidata")
                # Remove matching if present
                text = remove_category(text, "Matching pagename on wikidata")

            # Save the page
            try:
                page.edit(text, summary="Bot: categorize based on Wikidata P11250 property")
                processed_count += 1
            except mwclient.errors.EditConflict:
                print(f" ! Edit conflict")
                error_count += 1
            except Exception as e:
                print(f" ! Error saving: {e}")
                error_count += 1

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")
            error_count += 1

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  With P11250: {has_p11250_count}")
    print(f"  Matching pagename: {matching_count}")
    print(f"  Non-matching pagename: {non_matching_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main()
