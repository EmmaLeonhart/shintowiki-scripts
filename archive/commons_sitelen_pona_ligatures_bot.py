#!/usr/bin/env python
"""
Wikimedia Commons Bot - Add Word Categories to Sitelen Pona Ligatures
=====================================================================

For each subcategory in [[Category:Sitelen Pona ligatures]]:
1. Parse the category name pattern: "word1 word2 word3... (toki pona)"
2. Add [[Category:word1 (toki pona)]], [[Category:word2 (toki pona)]], etc.
"""

import sys
import io
import time
import re
import mwclient

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── CONFIG ─────────────────────────────────────────────────────────
COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"
BOT_USERNAME = "Immanuelle@ImmanuelleCommonsBot"
BOT_PASSWORD = "rctsl2fbuo3qa0ngj1q2eur5ookdbjir"
ROOT_CATEGORY = "Category:Sitelen Pona ligatures"
THROTTLE = 10.0  # seconds between edits (Commons is stricter)

# ── HELPER FUNCTIONS ───────────────────────────────────────────────

def get_subcategories(site, category_name):
    """Get all subcategories of a given category"""
    subcats = []
    for cm in site.api("query", list="categorymembers",
                       cmtitle=category_name, cmtype="subcat",
                       cmlimit="max")["query"]["categorymembers"]:
        subcats.append(cm["title"])
    return subcats

def parse_ligature_words(category_title):
    """
    Parse category title to extract words.
    Example: "Category:Iyo suwi (toki pona)" -> ["Iyo", "suwi"]
    Returns None if pattern doesn't match.
    """
    # Remove "Category:" prefix
    if category_title.startswith("Category:"):
        category_title = category_title[9:]

    # Match pattern: "word1 word2... (toki pona)"
    match = re.match(r'^(.+?)\s+\(toki pona\)$', category_title)
    if not match:
        return None

    words_part = match.group(1)
    words = words_part.split()

    # Filter out empty strings and return
    return [w for w in words if w]

def add_word_categories(site, category_title):
    """Add individual word categories to a ligature category"""
    words = parse_ligature_words(category_title)

    if not words:
        print(f"  ⚠ Does not match pattern: {category_title}")
        return 0

    if len(words) < 2:
        print(f"  ⚠ Only one word (not a ligature): {category_title}")
        return 0

    print(f"  Words: {words}")

    page = site.pages[category_title]
    if not page.exists:
        print(f"  ⚠ Page does not exist: {category_title}")
        return 0

    text = page.text()
    original_text = text
    added_count = 0

    # Add each word category if not already present
    for word in words:
        category_tag = f"[[Category:{word} (toki pona)]]"

        if category_tag in text:
            print(f"    • Already has: [[Category:{word} (toki pona)]]")
        else:
            text = text.rstrip() + f"\n{category_tag}\n"
            added_count += 1
            print(f"    + Adding: [[Category:{word} (toki pona)]]")

    # Save if we made changes
    if text != original_text:
        try:
            page.save(text, summary="")
            print(f"  ✓ Saved with {added_count} new categories")
            return added_count
        except Exception as e:
            print(f"  ✗ Failed to save: {e}")
            return 0
    else:
        print(f"  • No changes needed")
        return 0

# ── MAIN ───────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("WIKIMEDIA COMMONS - SITELEN PONA LIGATURES BOT")
    print("="*70)
    print()

    # Login to Commons
    print(f"Connecting to {COMMONS_URL}...")
    site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
    site.login(BOT_USERNAME, BOT_PASSWORD)
    print("Logged in successfully\n")

    # Get all subcategories
    print(f"Fetching subcategories of {ROOT_CATEGORY}...")
    subcats = get_subcategories(site, ROOT_CATEGORY)
    print(f"Found {len(subcats)} subcategories\n")

    # Process each subcategory
    total_categories_added = 0
    total_pages_modified = 0

    for idx, subcat in enumerate(subcats, 1):
        print(f"{idx}/{len(subcats)}: {subcat}")

        added = add_word_categories(site, subcat)
        if added > 0:
            total_categories_added += added
            total_pages_modified += 1

        print()
        time.sleep(THROTTLE)

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Pages modified: {total_pages_modified}")
    print(f"Categories added: {total_categories_added}")
    print("\nDone!")

if __name__ == "__main__":
    main()
