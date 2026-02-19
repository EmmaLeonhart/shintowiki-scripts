"""
Fetch Wikimedia Commons categories for Goshuincho images and generate updated wikitext
"""

import requests
import time
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Image numbers from the wiki page (extracted from wikitext)
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
            # Extract category names, removing "Category:" prefix
            cat_names = []
            for cat in categories:
                cat_title = cat.get('title', '')
                if cat_title.startswith('Category:'):
                    cat_name = cat_title[9:]  # Remove "Category:" prefix
                    # Filter out ignored categories (license, metadata, etc.)
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
    results = {}

    print("Fetching categories from Wikimedia Commons...")
    print("=" * 60)

    for num in image_numbers:
        filename = f"Goshuincho of Emma Leonhart {num:02d}.jpg"
        categories = get_file_categories(filename)
        results[num] = categories

        if categories:
            print(f"{num:02d}: {', '.join(categories)}")
        else:
            print(f"{num:02d}: (no categories found)")

        time.sleep(0.5)  # Rate limiting

    print("\n" + "=" * 60)
    print("Generating updated wikitext table...")
    print("=" * 60 + "\n")

    # Generate the updated table wikitext
    print('{| class="wikitable sortable"')
    print('! Image')
    print('! Shrine name')
    print('! Commons category')
    print('|-')

    for num in image_numbers:
        categories = results.get(num, [])
        cat_links = []
        for cat in categories:
            # Create link to Commons category
            cat_links.append(f'[[:commons:Category:{cat}|{cat}]]')

        cat_text = '<br>'.join(cat_links) if cat_links else ''

        print(f'| [[File:Goshuincho of Emma Leonhart {num:02d}.jpg|50px]] || || {cat_text}')
        print('|-')

    print('|}')

if __name__ == '__main__':
    main()
