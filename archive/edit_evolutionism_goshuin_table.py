"""
Edit the Leonhart Shrine page on evolutionism.miraheze.org to add Commons categories column
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
WIKI_URL  = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
PAGE_NAME = 'Leonhart Shrine'

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Image numbers from the wiki page
image_numbers = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
    40, 41, 42, 43, 44, 45, 46, 47,
    50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
    60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
    70, 71, 73, 74, 75, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94
]

# Categories to ignore (license, metadata, etc.)
IGNORE_PATTERNS = [
    "Goshuincho",
    "CC-BY",
    "Creative Commons",
    "Self-published",
    "SDC",
    "license",
    "Files by",
    "Files from",
    "Uploaded via",
    "Media missing",
    "Images with",
    "PD-",
    "GFDL",
    "Duplicate",
    "Unidentified",
    "bad uploads",
    "Immanuelle's Goshuin"
]

def get_file_categories(filename):
    """Fetch categories for a file from Wikimedia Commons"""
    params = {
        'action': 'query',
        'titles': f'File:{filename}',
        'prop': 'categories',
        'cllimit': 'max',
        'format': 'json'
    }

    try:
        r = requests.get(COMMONS_API, params=params, headers={'User-Agent': 'WikiBot/1.0'})
        data = r.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id == '-1':
                return []

            categories = page_data.get('categories', [])
            cat_names = []
            for cat in categories:
                cat_title = cat.get('title', '')
                if cat_title.startswith('Category:'):
                    cat_name = cat_title[9:]
                    should_ignore = False
                    for pattern in IGNORE_PATTERNS:
                        if pattern.lower() in cat_name.lower():
                            should_ignore = True
                            break
                    if not should_ignore:
                        cat_names.append(cat_name)
            return cat_names
    except Exception as e:
        print(f"Error fetching {filename}: {e}")
        return []

def main():
    # Connect to wiki
    print(f"Connecting to {WIKI_URL}...")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent='WikiBot/1.0 (https://evolutionism.miraheze.org/; immanuelle@example.com)')
    site.login(USERNAME, PASSWORD)
    print("Logged in successfully!\n")

    # Fetch Commons categories
    print("Fetching categories from Wikimedia Commons...")
    results = {}
    for num in image_numbers:
        filename = f"Goshuincho of Emma Leonhart {num:02d}.jpg"
        categories = get_file_categories(filename)
        results[num] = categories
        if categories:
            print(f"  {num:02d}: {', '.join(categories)}")
        else:
            print(f"  {num:02d}: (no categories)")
        time.sleep(0.3)

    # Get current page content
    print(f"\nFetching page: {PAGE_NAME}")
    page = site.pages[PAGE_NAME]
    old_text = page.text()

    # Build new Goshuin table
    new_table_lines = ['{| class="wikitable sortable"', '! Image', '! Shrine name', '! Commons category', '|-']

    for num in image_numbers:
        categories = results.get(num, [])
        cat_links = []
        for cat in categories:
            cat_links.append(f'[[:commons:Category:{cat}|{cat}]]')
        cat_text = '<br>'.join(cat_links) if cat_links else ''
        new_table_lines.append(f'| [[File:Goshuincho of Emma Leonhart {num:02d}.jpg|50px]] || || {cat_text}')
        new_table_lines.append('|-')

    new_table_lines.append('|}')
    new_table = '\n'.join(new_table_lines)

    # Find and replace the Goshuin table
    # The table starts after "== Goshuin ==" and ends before "== Deities =="
    goshuin_section_pattern = r'(== Goshuin ==\s*\n)(\{\|.*?\|\})'

    match = re.search(goshuin_section_pattern, old_text, re.DOTALL)
    if match:
        new_text = old_text[:match.start(2)] + new_table + old_text[match.end(2):]

        # Save the page
        print("\nSaving page...")
        page.save(new_text, summary="Add Commons category column to Goshuin table")
        print("Done!")
    else:
        print("ERROR: Could not find Goshuin table in page!")
        print("Trying alternative approach...")

        # Alternative: find the table after "== Goshuin =="
        goshuin_header_pos = old_text.find('== Goshuin ==')
        if goshuin_header_pos == -1:
            print("Could not find Goshuin section!")
            return

        # Find the table start after the header
        table_start = old_text.find('{|', goshuin_header_pos)
        if table_start == -1:
            print("Could not find table start!")
            return

        # Find the table end
        table_end = old_text.find('|}', table_start) + 2
        if table_end < 2:
            print("Could not find table end!")
            return

        new_text = old_text[:table_start] + new_table + old_text[table_end:]

        print("\nSaving page...")
        page.save(new_text, summary="Add Commons category column to Goshuin table")
        print("Done!")

if __name__ == '__main__':
    main()
