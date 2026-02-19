#!/usr/bin/env python
"""
Wikimedia Commons Bot - Add Worship/Enshrinement Categories Based on Wikidata
===============================================================================

For worship/enshrinement-based shrine categories:
1. Get the Wikidata item for the Commons category
2. Get the category's main topic (P301) if it's a Wikimedia category
3. Find all items where P31 (instance of) = P301 value
4. Get their Commons categories (P373)
5. Add the category to those Commons category pages

All categories use P31 (instance of) property.
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

# ── CATEGORY DEFINITIONS ───────────────────────────────────────────

# All P31 categories from the worship/enshrinement list
CATEGORIES = [
    "Akagi-jinja",
    "Akiha-jinja (worship)",
    "Aso-jinja (worship)",
    "Atago-jinja",
    "Aviation shrines",
    "Awashima-jinja (worship)",
    "Benzaiten shrines",
    "Dairokuten jinjya",
    "Daishōgun-jinja",
    "Ebisu-jinja",
    "Emperor Sudo Shrines",
    "Gion Shrines",
    "Goō-jinja (worship)",
    "Hachiken-sha Shrine",
    "Hachiman shrines",
    "Haguro-jinja",
    "Hakusan-jinja",
    "Haraedo shrines",
    "Haruna-jinja (worship)",
    "Hikawa-jinja",
    "Hitokotonushi-jinja",
    "Hyōzu-jinja",
    "Iizuna-jinja (worship)",
    "Inari-jinja",
    "Irou-jinja",
    "Itsukushima-jinja (worship)",
    "Iwafune-jinja",
    "Izanagi-jinja",
    "Izanami-jinja (worship)",
    "Kamo-jinja (worship)",
    "Kashima shrines",
    "Kasuga-jinja",
    "Katori-jinja",
    "Keta-jinja (worship)",
    "Kifune-jinja (worship)",
    "Konsei-jinja",
    "Kotohira-jinja (worship)",
    "Kumano shrines",
    "Kuzuryū-jinja",
    "Kōjin shrines",
    "Kōshin-sha",
    "Matsuo shrines",
    "Mikumari-jinja",
    "Mishima-jinja (worship)",
    "Mitsumine-jinja (worship)",
    "Miwa-jinja",
    "Mononobe-jinja",
    "Munakata-jinja",
    "Myōken shrines",
    "Niu-jinja (worship)",
    "Nogi-jinja",
    "Nyakuichi-ōji shrines",
    "Ōkuninushi-jinja (worship)",
    "Onsen-jinja",
    "Ontake-jinja",
    "Ootoshi-jinja",
    "Saba-jinja",
    "Sannō-jinja",
    "Sarutahiko-jinja (worship)",
    "Sengen-jinja",
    "Shinmei-jinja",
    "Shiogama-jinja (worship)",
    "Shirahata-jinja",
    "Shirahige-jinja (worship)",
    "Suga-jinja (worship)",
    "Sugiyama-jinja (Musashi Province)",
    "Suijin shrines",
    "Suiten-gū",
    "Sukunahikona-jinja (worship)",
    "Sumiyoshi-jinja",
    "Susanoo-Jinja",
    "Suwa-jinja",
    "Taga-jinja",
    "Tajikarao-jinja",
    "Takeuchi-jinja (worship)",
    "Tenman-gū",
    "Tōshō-gū",
    "Tsukiyomi-jinja",
    "Tsushima-jinja",
    "Uga-jinja",
    "Yakumo-jinja",
    "Yasaka-jinja",
    "Ōtori-jinja (worship)",
    "Ōyamazumi-jinja (worship)",
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
    print("WIKIMEDIA COMMONS - WORSHIP/ENSHRINEMENT CATEGORIES BOT")
    print("="*70)
    print()

    # Login to Commons
    print(f"Connecting to {COMMONS_URL}...")
    site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
    site.login(BOT_USERNAME, BOT_PASSWORD)
    print("Logged in successfully\n")

    total_categories_added = 0
    total_pages_modified = 0

    # Process all categories
    print(f"Processing {len(CATEGORIES)} categories...")
    print("="*70)

    for idx, cat_name in enumerate(CATEGORIES, 1):
        print(f"\n{idx}/{len(CATEGORIES)}: {cat_name} (P31)")

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

        # Step 3: Find all items where P31 = topic_qid
        results = find_items_with_property_value(topic_qid, "P31")
        print(f"  Found {len(results)} items with Commons categories")

        if not results:
            print(f"  ⚠ No items found")
            continue

        # Step 4: Add category to each Commons page
        for item_qid, commons_cat in results:
            print(f"    {item_qid}: Category:{commons_cat}")
            if add_category_to_commons_page(site, commons_cat, cat_name):
                total_categories_added += 1
                total_pages_modified += 1
            time.sleep(THROTTLE)

    # Summary
    print("\n")
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Pages modified: {total_pages_modified}")
    print(f"Categories added: {total_categories_added}")
    print("\nDone!")

if __name__ == "__main__":
    main()
