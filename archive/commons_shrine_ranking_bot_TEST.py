#!/usr/bin/env python
"""
TEST VERSION - Wikimedia Commons Bot - Add Shrine Ranking Categories
=====================================================================

Tests one category from each property type, processing only ONE item per category.
"""

import sys
import io
import time
import requests
import urllib.parse
import mwclient

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── CONFIG ─────────────────────────────────────────────────────────
COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"
BOT_USERNAME = "Immanuelle@ImmanuelleCommonsBot"
BOT_PASSWORD = "rctsl2fbuo3qa0ngj1q2eur5ookdbjir"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
THROTTLE = 10.0  # seconds between edits

# ── ALL CATEGORIES (testing one item per category) ────────────────

CATEGORIES = [
    # P31 categories
    ("Beppyo Shrines", "P31"),
    ("Chokusaisha", "P31"),
    ("Gokoku shrines", "P31"),
    ("Jingū", "P31"),
    ("Kokushi genzaisha", "P31"),
    ("Shikigesha", "P31"),
    ("Taisha (Shinto)", "P31"),
    ("Shikinai Taisha", "P31"),
    ("Shikinai Ronsha", "P31"),
    ("Shikinai Shosha", "P31"),
    ("Myōjin Taisha", "P31"),
    ("Disputed Shikinaisha", "P31"),
    ("Regional Sōja", "P31"),
    ("Kanpei-sha", "P31"),
    ("Kokuhei-sha", "P31"),
    ("Shrines dedicated to Empress Jingū", "P31"),
    ("Shrine receiving Tsukinami-sai and Niiname-sai and Ainame-sai offerings", "P31"),
    ("Shrine receiving Tsukinami-sai and Niiname-sai offerings", "P31"),
    ("Shrines receiving Hoe and Quiver", "P31"),
    ("Shrines receiving Hoe offering", "P31"),
    ("Shrines receiving Quiver offering", "P31"),
    ("Ichinomiya", "P31"),
    ("Regional Ichinomiya", "P31"),
    ("Ni-no-Miya", "P31"),
    ("San-no-Miya", "P31"),
    ("Shi-no-Miya", "P31"),
    ("Go-no-Miya", "P31"),
    ("Roku-no-Miya", "P31"),

    # P13723 categories (Modern system)
    ("Bekkaku Kanpeisha", "P13723"),
    ("Fu-sha", "P13723"),
    ("Fuken-sha", "P13723"),
    ("Gō-sha", "P13723"),
    ("Kanpei Chūsha", "P13723"),
    ("Kanpei Shōsha", "P13723"),
    ("Kanpei Taisha", "P13723"),
    ("Ken-sha", "P13723"),
    ("Kokuhei Chūsha", "P13723"),
    ("Kokuhei Shōsha", "P13723"),
    ("Kokuhei Taisha", "P13723"),
    ("Min-sha", "P13723"),
    ("Son-sha", "P13723"),
    ("Unranked shrines", "P13723"),

    # P149 categories (Architectural style)
    ("Gion-zukuri", "P149"),
    ("Hachiman-zukuri", "P149"),
    ("Hiyoshi-zukuri", "P149"),
    ("Ishi-no-ma-zukuri", "P149"),
    ("Kashii-zukuri", "P149"),
    ("Kasuga-zukuri", "P149"),
    ("Kibitsu-zukuri", "P149"),
    ("Nagare-zukuri", "P149"),
    ("Nakayama-zukuri", "P149"),
    ("Oki-zukuri", "P149"),
    ("Owari-zukuri", "P149"),
    ("Sengen-zukuri", "P149"),
    ("Shinmei-zukuri", "P149"),
    ("Sumiyoshi-zukuri", "P149"),
    ("Taisha-zukuri", "P149"),
    ("Ōtori-zukuri", "P149"),

    # P361 categories - Shikinaisha by Province
    ("Shikinaisha in Aki Province", "P361"),
    ("Shikinaisha in Awa Province (Chiba)", "P361"),
    ("Shikinaisha in Awa Province (Tokushima)", "P361"),
    ("Shikinaisha in Awaji Province", "P361"),
    ("Shikinaisha in Bingo Province", "P361"),
    ("Shikinaisha in Bitchū Province", "P361"),
    ("Shikinaisha in Bizen Province", "P361"),
    ("Shikinaisha in Bungo Province", "P361"),
    ("Shikinaisha in Buzen Province", "P361"),
    ("Shikinaisha in Chikugo Province", "P361"),
    ("Shikinaisha in Chikuzen Province", "P361"),
    ("Shikinaisha in Dewa Province", "P361"),
    ("Shikinaisha in Echigo Province", "P361"),
    ("Shikinaisha in Echizen Province", "P361"),
    ("Shikinaisha in Etchū Province", "P361"),
    ("Shikinaisha in Harima Province", "P361"),
    ("Shikinaisha in Hida Province", "P361"),
    ("Shikinaisha in Higo Province", "P361"),
    ("Shikinaisha in Hitachi Province", "P361"),
    ("Shikinaisha in Hizen Province", "P361"),
    ("Shikinaisha in Hyūga Province", "P361"),
    ("Shikinaisha in Hōki Province", "P361"),
    ("Shikinaisha in Iga Province", "P361"),
    ("Shikinaisha in Iki Island", "P361"),
    ("Shikinaisha in Inaba Province", "P361"),
    ("Shikinaisha in Ise Province", "P361"),
    ("Shikinaisha in Iwami Province", "P361"),
    ("Shikinaisha in Iyo Province", "P361"),
    ("Shikinaisha in Izu Province", "P361"),
    ("Shikinaisha in Izumi Province", "P361"),
    ("Shikinaisha in Izumo Province", "P361"),
    ("Shikinaisha in Kaga Province", "P361"),
    ("Shikinaisha in Kai Province", "P361"),
    ("Shikinaisha in Kawachi Province", "P361"),
    ("Shikinaisha in Kazusa Province", "P361"),
    ("Shikinaisha in Kii Province", "P361"),
    ("Shikinaisha in Kōzuke Province", "P361"),
    ("Shikinaisha in Mikawa Province", "P361"),
    ("Shikinaisha in Mimasaka Province", "P361"),
    ("Shikinaisha in Mino Province", "P361"),
    ("Shikinaisha in Musashi Province", "P361"),
    ("Shikinaisha in Mutsu Province", "P361"),
    ("Shikinaisha in Nagato Province", "P361"),
    ("Shikinaisha in Noto Province", "P361"),
    ("Shikinaisha in Oki Province", "P361"),
    ("Shikinaisha in Owari Province", "P361"),
    ("Shikinaisha in Sado Province", "P361"),
    ("Shikinaisha in Sanuki Province", "P361"),
    ("Shikinaisha in Satsuma Province", "P361"),
    ("Shikinaisha in Settsu Province", "P361"),
    ("Shikinaisha in Shima Province", "P361"),
    ("Shikinaisha in Shimotsuke Province", "P361"),
    ("Shikinaisha in Shimōsa Province", "P361"),
    ("Shikinaisha in Shinano Province", "P361"),
    ("Shikinaisha in Suo Province", "P361"),
    ("Shikinaisha in Suruga Province", "P361"),
    ("Shikinaisha in Tajima Province", "P361"),
    ("Shikinaisha in Tanba Province", "P361"),
    ("Shikinaisha in Tango Province", "P361"),
    ("Shikinaisha in the Imperial Palace", "P361"),
    ("Shikinaisha in Tosa Province", "P361"),
    ("Shikinaisha in Tsushima", "P361"),
    ("Shikinaisha in Tōtōmi Province", "P361"),
    ("Shikinaisha in Wakasa Province", "P361"),
    ("Shikinaisha in Yamashiro Province", "P361"),
    ("Shikinaisha in Yamato Province", "P361"),
    ("Shikinaisha in Ōmi Province", "P361"),
    ("Shikinaisha in Ōsumi Province", "P361"),
]

# ── HELPER FUNCTIONS ───────────────────────────────────────────────

def get_wikidata_item_for_commons_category(category_name):
    """
    Get the Wikidata item QID for a Commons category.
    Uses Wikidata API to get entity from Commons sitelink.
    """
    headers = {'User-Agent': 'ImmanuelleCommonsBot/1.0'}

    try:
        # Use Wikidata API to get entity from Commons sitelink
        params = {
            'action': 'wbgetentities',
            'sites': 'commonswiki',
            'titles': f'Category:{category_name}',
            'format': 'json'
        }

        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'entities' in data:
            for qid, entity in data['entities'].items():
                if qid != '-1' and 'missing' not in entity:
                    return qid

        return None

    except Exception as e:
        print(f"  ✗ Failed to get Wikidata item: {e}")
        return None

def is_wikimedia_category(qid):
    """
    Check if item is instance of Wikimedia category (Q4167836).
    """
    query = f"""
    ASK {{
      wd:{qid} wdt:P31 wd:Q4167836 .
    }}
    """

    headers = {'User-Agent': 'ImmanuelleCommonsBot/1.0'}

    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get('boolean', False)

    except Exception as e:
        print(f"  ✗ Failed to check if Wikimedia category: {e}")
        return False

def get_main_topic(qid):
    """
    Get the main topic (P301) of a Wikidata category item.
    """
    query = f"""
    SELECT ?topic WHERE {{
      wd:{qid} wdt:P301 ?topic .
    }}
    LIMIT 1
    """

    headers = {'User-Agent': 'ImmanuelleCommonsBot/1.0'}

    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data['results']['bindings']:
            topic_url = data['results']['bindings'][0]['topic']['value']
            topic_qid = topic_url.split('/')[-1]
            return topic_qid
        return None

    except Exception as e:
        print(f"  ✗ Failed to get main topic: {e}")
        return None

def find_items_with_property_value(topic_qid, property_type):
    """
    Find all items where property = topic_qid, and get their Commons categories.
    """
    query = f"""
    SELECT DISTINCT ?item ?commonsCategory WHERE {{
      ?item wdt:{property_type} wd:{topic_qid} .
      ?item wdt:P373 ?commonsCategory .
    }}
    """

    headers = {'User-Agent': 'ImmanuelleCommonsBot/1.0'}

    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for binding in data['results']['bindings']:
            commons_cat = binding['commonsCategory']['value']
            item_qid = binding['item']['value'].split('/')[-1]
            results.append((item_qid, commons_cat))

        return results

    except Exception as e:
        print(f"  ✗ SPARQL query failed: {e}")
        return []

def add_category_to_commons_page(site, commons_category_name, category_to_add):
    """Add a category to a Commons category page"""
    page_title = f"Category:{commons_category_name}"
    page = site.pages[page_title]

    if not page.exists:
        print(f"      ⚠ Page does not exist: {page_title}")
        return False

    text = page.text()
    category_tag = f"[[Category:{category_to_add}]]"

    if category_tag in text:
        print(f"      • Already has category")
        return False

    # Add category at the end
    new_text = text.rstrip() + f"\n{category_tag}\n"

    try:
        page.save(new_text, summary="")
        print(f"      ✓ Added [[Category:{category_to_add}]]")
        return True
    except Exception as e:
        print(f"      ✗ Failed to save: {e}")
        return False

# ── MAIN ───────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("TEST - WIKIMEDIA COMMONS - SHRINE RANKING CATEGORIES BOT")
    print("Testing ONE item from EACH of the 105 categories")
    print("="*70)
    print()

    # Login to Commons
    print(f"Connecting to {COMMONS_URL}...")
    site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
    site.login(BOT_USERNAME, BOT_PASSWORD)
    print("Logged in successfully\n")

    total_categories_added = 0
    total_pages_modified = 0

    # Process test categories
    print(f"Processing {len(CATEGORIES)} test categories...")
    print("="*70)

    for idx, (cat_name, prop_type) in enumerate(CATEGORIES, 1):
        print(f"\n{idx}/{len(CATEGORIES)}: {cat_name} ({prop_type})")

        # Step 1: Get Wikidata item for the Commons category
        cat_qid = get_wikidata_item_for_commons_category(cat_name)
        if not cat_qid:
            print(f"  ⚠ No Wikidata item found for this Commons category")
            continue
        print(f"  Category item: {cat_qid}")

        # Step 2: Determine the topic QID
        # If item is instance of Wikimedia category, get P301 (main topic)
        # Otherwise, use the item itself as the topic
        if is_wikimedia_category(cat_qid):
            print(f"  Is Wikimedia category, looking for P301...")
            topic_qid = get_main_topic(cat_qid)
            if not topic_qid:
                print(f"  ⚠ No main topic (P301) found")
                continue
            print(f"  Main topic (P301): {topic_qid}")
        else:
            # Not a Wikimedia category - use the item itself as the topic
            topic_qid = cat_qid
            print(f"  Not a Wikimedia category, using item as topic: {topic_qid}")

        # Step 3: Find all items where property = topic_qid
        results = find_items_with_property_value(topic_qid, prop_type)
        print(f"  Found {len(results)} items total with Commons categories")

        if not results:
            print(f"  ⚠ No items found")
            continue

        # TEST: Try items until we find one that doesn't already have the category
        added = False
        for item_qid, commons_cat in results:
            print(f"  Trying: {item_qid}: Category:{commons_cat}")
            result = add_category_to_commons_page(site, commons_cat, cat_name)
            if result:
                total_categories_added += 1
                total_pages_modified += 1
                added = True
                time.sleep(THROTTLE)
                break
            elif result is False:
                # Check if it was "already has category" - if so, try next item
                # If it was a different error (page doesn't exist), also try next
                continue

        if not added:
            print(f"  All items already have category or failed")

        time.sleep(2)  # Small delay between categories

    # Summary
    print("\n")
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Pages modified: {total_pages_modified}")
    print(f"Categories added: {total_categories_added}")
    print("\nTest complete!")

if __name__ == "__main__":
    main()
