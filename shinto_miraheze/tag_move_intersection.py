"""
Find pages in both Category:Move_starting_points AND Category:Move_targets,
then add [[Category:Move targets ∩ destinations]] to any not already there.

Pages in both categories are "difficult edge cases" - they were moved TO (they
are a destination) but also still NEED to be moved (they are a starting point).
"""

import mwclient
import time
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.5

CAT_STARTING  = 'Move starting points'
CAT_TARGETS   = 'Move targets'
CAT_INTERSECT = 'Move targets ∩ destinations'


def get_category_pages(site, cat_name):
    """Return a set of page titles (namespace-prefixed) from a category."""
    titles = set()
    cat = site.categories[cat_name]
    for page in cat:
        titles.add(page.name)
    return titles


def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL}\n")

    print("Fetching category members...")
    starting_points = get_category_pages(site, CAT_STARTING)
    targets         = get_category_pages(site, CAT_TARGETS)
    already_tagged  = get_category_pages(site, CAT_INTERSECT)

    print(f"  Move starting points : {len(starting_points)} pages")
    print(f"  Move targets         : {len(targets)} pages")
    print(f"  Already in ∩ cat     : {len(already_tagged)} pages")

    intersection = starting_points & targets
    to_tag = intersection - already_tagged

    print(f"\nIntersection (both categories) : {len(intersection)} pages")
    print(f"Still need ∩ category tag      : {len(to_tag)} pages")

    if not to_tag:
        print("\nNothing to do - all intersection pages already tagged.")
        return

    print("\nPages to tag:")
    for t in sorted(to_tag):
        print(f"  {t}")

    cat_tag = f"[[Category:{CAT_INTERSECT}]]"
    done = 0
    skipped = 0
    errors = 0

    for i, title in enumerate(sorted(to_tag), 1):
        print(f"\n[{i}/{len(to_tag)}] {title}")
        page = site.pages[title]
        if not page.exists:
            print("  SKIP - page does not exist")
            skipped += 1
            continue

        text = page.text() or ""

        if cat_tag in text:
            print("  SKIP - category tag already present")
            skipped += 1
            continue

        new_text = text.rstrip() + "\n" + cat_tag + "\n"
        try:
            page.save(new_text, summary=f"Bot: Tagging as move ∩ (both starting point and destination)")
            print("  SAVED")
            done += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

        time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"Done! Tagged: {done}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
