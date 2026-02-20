"""
remove_crud_categories.py
==========================
Removes all crud category tags from pages.

For every subcategory of Category:Crud_categories:
  - Iterate all member pages
  - Strip [[Category:SubcatName]] (and variants with sort keys) from each page
  - After processing, the subcategory should be empty

Run dry-run first:
    python remove_crud_categories.py --dry-run
"""

import re
import time
import io
import sys
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 1.5
CRUD_CAT   = "Crud_categories"


def make_cat_pattern(cat_name):
    """Return a regex that matches [[Category:Name]] or [[Category:Name|sortkey]]."""
    escaped = re.escape(cat_name).replace(r'\ ', r'[_ ]')
    return re.compile(
        r'\[\[Category:' + escaped + r'(\|[^\]]*)?\]\]\n?',
        re.IGNORECASE
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="CrudCategoryRemoverBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    crud_cat = site.categories[CRUD_CAT]
    subcats = [p for p in crud_cat if p.namespace == 14]
    print(f"Found {len(subcats)} subcategories of Category:{CRUD_CAT}\n")

    total_edits = 0

    for subcat in subcats:
        subcat_name = subcat.name.removeprefix("Category:")
        print(f"--- Category:{subcat_name} ---")
        pattern = make_cat_pattern(subcat_name)
        members = list(site.categories[subcat_name])

        if not members:
            print(f"  Already empty, skipping.\n")
            continue

        print(f"  {len(members)} members to clean")
        for page in members:
            text = page.text()
            new_text = pattern.sub("", text).rstrip("\n")
            if new_text == text.rstrip("\n"):
                print(f"  SKIP (tag not found): {page.name}")
                continue
            if args.dry_run:
                print(f"  DRY RUN: would strip [[Category:{subcat_name}]] from {page.name}")
            else:
                page.save(new_text, summary=f"Bot: remove [[Category:{subcat_name}]] (crud category cleanup)")
                print(f"  CLEANED: {page.name}")
                time.sleep(THROTTLE)
                total_edits += 1

        print()

    print(f"{'='*60}")
    print(f"Done! Total edits: {total_edits}")


if __name__ == "__main__":
    main()
