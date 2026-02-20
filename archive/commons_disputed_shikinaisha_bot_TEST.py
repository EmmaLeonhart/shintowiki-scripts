#!/usr/bin/env python
"""
Wikimedia Commons Bot - Add Disputed Shikinaisha Categories (TEST VERSION)
===========================================================================

TEST: Only processes Enano Shrine (Q135039909)
"""

import sys
import io
import csv
import time
import urllib.parse
from collections import defaultdict
import mwclient

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── CONFIG ─────────────────────────────────────────────────────────
COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"
BOT_USERNAME = "Immanuelle@ImmanuelleCommonsBot"
BOT_PASSWORD = "rctsl2fbuo3qa0ngj1q2eur5ookdbjir"
CSV_FILE = r"C:\Users\Immanuelle\Downloads\query (2).csv"
THROTTLE = 2.0  # seconds between edits (Commons is stricter)

# TEST: Only process this one disputed shrine
TEST_QID = "Q135039909"  # Enano Shrine

# ── HELPER FUNCTIONS ───────────────────────────────────────────────

def extract_qid(url):
    """Extract QID from Wikidata URL"""
    return url.split('/')[-1]

def extract_category_name(commons_url):
    """Extract category name from Commons URL"""
    # https://commons.wikimedia.org/wiki/Category:Ena-jinja%20%28Takayama%29
    parsed = urllib.parse.urlparse(commons_url)
    path = parsed.path
    # Remove /wiki/Category: prefix
    cat_encoded = path.replace('/wiki/Category:', '')
    # URL decode
    cat_name = urllib.parse.unquote(cat_encoded)
    return cat_name

def load_csv_data():
    """Load and group CSV data by disputed shrine"""
    disputed_groups = defaultdict(lambda: {
        'qid': None,
        'label': None,
        'candidates': []
    })

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            disputed_url = row['disputed']
            disputed_label = row['disputedLabel']
            commons_cat_url = row['commonsCategory']

            qid = extract_qid(disputed_url)

            # TEST: Only process TEST_QID
            if qid != TEST_QID:
                continue

            key = (qid, disputed_label)

            disputed_groups[key]['qid'] = qid
            disputed_groups[key]['label'] = disputed_label
            disputed_groups[key]['candidates'].append(commons_cat_url)

    return disputed_groups

def add_category_to_page(site, page_title, category_name):
    """Add a category to a Commons page if not already present"""
    page = site.pages[page_title]

    if not page.exists:
        print(f"      ⚠ Page does not exist: {page_title}")
        return False

    text = page.text()
    category_tag = f"[[Category:{category_name}]]"

    if category_tag in text:
        print(f"      • Already has category: {page_title}")
        return False

    # Add category at the end
    new_text = text.rstrip() + f"\n{category_tag}\n"

    try:
        page.save(new_text, summary=f"Bot: Add [[Category:{category_name}]] (disputed Shikinaisha)")
        print(f"      ✓ Added category to: {page_title}")
        return True
    except Exception as e:
        print(f"      ✗ Failed to save {page_title}: {e}")
        return False

def create_disputed_category(site, category_name, qid):
    """Create the disputed shrine category page"""
    page_title = f"Category:{category_name}"
    page = site.pages[page_title]

    if page.exists:
        text = page.text()
        # Check if it already has the correct content
        if f"qid = {qid}" in text and "[[Category:Disputed Shikinaisha]]" in text:
            print(f"    • Category already exists with correct content: {category_name}")
            return False

    # Create the page content
    content = f"""{{{{Wikidata Infobox
| qid = {qid}
}}}}
[[Category:Disputed Shikinaisha]]
"""

    try:
        page.save(content, summary=f"Bot: Create disputed Shikinaisha category (QID: {qid})")
        print(f"    ✓ Created category: {category_name}")
        return True
    except Exception as e:
        print(f"    ✗ Failed to create category {category_name}: {e}")
        return False

# ── MAIN ───────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("WIKIMEDIA COMMONS - DISPUTED SHIKINAISHA BOT (TEST)")
    print("="*70)
    print(f"TEST MODE: Only processing {TEST_QID}")
    print()

    # Load CSV data
    print("Loading CSV data...")
    disputed_groups = load_csv_data()

    if not disputed_groups:
        print(f"ERROR: Could not find {TEST_QID} in CSV!")
        return

    print(f"Found test shrine\n")

    # Login to Commons
    print(f"Connecting to {COMMONS_URL}...")
    site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
    site.login(BOT_USERNAME, BOT_PASSWORD)
    print("Logged in successfully\n")

    # Process the test shrine
    total_cats_added = 0
    total_cats_created = 0

    for idx, ((qid, label), data) in enumerate(disputed_groups.items(), 1):
        print(f"Processing: {label} ({qid})")
        print(f"  Candidates: {len(data['candidates'])}")

        # First, create the disputed category page
        print(f"\n  Step 1: Creating disputed category page...")
        if create_disputed_category(site, label, qid):
            total_cats_created += 1
            time.sleep(THROTTLE)

        # Then, add the category to all candidate pages
        print(f"\n  Step 2: Adding category to candidate pages...")
        for commons_url in data['candidates']:
            cat_name = extract_category_name(commons_url)
            page_title = f"Category:{cat_name}"
            print(f"    Processing: {page_title}")

            if add_category_to_page(site, page_title, label):
                total_cats_added += 1

            time.sleep(THROTTLE)

        print()

    # Summary
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Disputed categories created: {total_cats_created}")
    print(f"Categories added to candidate pages: {total_cats_added}")
    print("\n✓ Test completed successfully!")
    print("\nIf this looks good, run the full version:")
    print("  python commons_disputed_shikinaisha_bot.py")

if __name__ == "__main__":
    main()
