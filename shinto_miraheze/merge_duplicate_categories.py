#!/usr/bin/env python3
"""
Merge duplicate category pages by appending content from one to the other.
Both categories will end up with identical content.
"""

import mwclient
import time
import sys

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

# Initialize and login to the site
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# List of duplicate category pairs (from User:Immanuelle/Wikidata_duplicates)
duplicate_pairs = [
    ("Category:History of Setouchi", "Category:History of Setouchi, Okayama"),
    ("Category:Buildings in Chigasaki City", "Category:Buildings in Chigasaki, Kanagawa"),
    ("Category:Buildings in Toyooka", "Category:Buildings in Toyooka City"),
    ("Category:Buildings in Hanno City", "Category:Buildings in Hanno, Saitama"),
    ("Category:Ancient Japan-Korea relations", "Category:Japan–Korea Relations in Antiquity"),
    ("Category:Buildings in Kanagawa Ward", "Category:Buildings in Kanagawa-ku, Yokohama"),
    ("Category:Buildings in Higashiyama Ward", "Category:Buildings in Higashiyama-ku, Kyoto"),
    ("Category:Buildings in Kokura-Kita Ward", "Category:Buildings in Kokurakita-ku, Kitakyushu"),
    ("Category:Fukushima Prefecture by Municipality", "Category:fukushima prefecture by municipality"),
    ("Category:Archaeological Sites in Japan by Prefecture", "Category:archaeological sites in japan by prefecture"),
    ("Category:Archaeological sites in Japan by period", "Category:archaeological sites in japan by period"),
    ("Category:Buildings in Itoshima City", "Category:Buildings in Itoshima, Fukuoka"),
    ("Category:11th-century deaths", "Category:11世紀没"),
    ("Category:Japanese deities", "Category:Japanese gods"),
    ("Category:Historic monuments of ancient Nara", "Category:Historic monuments of nara"),
    ("Category:Former Prefectural Shrines in Wakayama Prefecture", "Category:Former prefectural shrines in wakayama"),
    ("Category:History of Tenri City", "Category:History of Tenri, Nara"),
    ("Category:Former Prefectural Shrines in Yamagata", "Category:Former prefectural shrines in yamagata"),
    ("Category:Former Prefectural Shrines in Yamanashi", "Category:Former prefectural shrines in yamanishi"),
    ("Category:History of Aichi Prefecture by Municipality", "Category:history of aichi prefecture by municipality"),
]

def merge_categories(cat1_name, cat2_name):
    """
    Merge two duplicate category pages.
    Append content from cat2 to cat1, then update both pages with identical content.
    """
    try:
        cat1 = site.pages[cat1_name]
        cat2 = site.pages[cat2_name]

        # Get content from both pages
        try:
            content1 = cat1.text()
        except:
            print(f"⚠️  {cat1_name} does not exist, skipping pair")
            return False

        try:
            content2 = cat2.text()
        except:
            print(f"⚠️  {cat2_name} does not exist, skipping pair")
            return False

        # Check if they're already identical
        if content1 == content2:
            print(f"✓ {cat1_name} and {cat2_name} already have identical content")
            return True

        # Merge content: combine them, avoiding duplicate lines
        lines1 = set(content1.split('\n'))
        lines2 = set(content2.split('\n'))
        merged_lines = sorted(lines1 | lines2)
        merged_content = '\n'.join(merged_lines)

        # Update both pages with merged content
        cat1.edit(merged_content, summary="Merging duplicate category - appending content from [[{}]]".format(cat2_name))
        print(f"✓ Updated {cat1_name}")
        time.sleep(0.5)  # Rate limiting

        cat2.edit(merged_content, summary="Merging duplicate category - content merged with [[{}]]".format(cat1_name))
        print(f"✓ Updated {cat2_name}")
        time.sleep(0.5)  # Rate limiting

        return True

    except Exception as e:
        print(f"❌ Error merging {cat1_name} and {cat2_name}: {str(e)}")
        return False

def main():
    """Process all duplicate category pairs."""
    print(f"Starting to merge {len(duplicate_pairs)} duplicate category pairs...\n")

    successful = 0
    failed = 0
    skipped = 0

    for i, (cat1, cat2) in enumerate(duplicate_pairs, 1):
        print(f"[{i}/{len(duplicate_pairs)}] Merging: {cat1} <-> {cat2}")

        if merge_categories(cat1, cat2):
            successful += 1
        else:
            failed += 1
        print()

    print("\n" + "="*60)
    print(f"Summary:")
    print(f"  ✓ Successful merges: {successful}")
    print(f"  ❌ Failed merges: {failed}")
    print(f"  ⚠️  Skipped: {skipped}")
    print("="*60)

if __name__ == "__main__":
    main()
