"""
tag_missing_wikidata_with_ja_interwiki.py
==========================================
Goes through Category:Categories_missing_wikidata and finds any
category page that has a Japanese interwiki link ([[ja:...]]).

Tags those pages with [[Category:Categories missing Wikidata with Japanese interwikis]]
so they can be batch-processed later (the ja: link can be used to look
up the QID from jawiki).

Creates the target category page if it doesn't exist.

Run dry-run first:
    python tag_missing_wikidata_with_ja_interwiki.py --dry-run
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
USERNAME   = "EmmaBot"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 1.5

SOURCE_CAT = "Categories_missing_wikidata"
TARGET_CAT = "Categories missing Wikidata with Japanese interwikis"

JA_RE      = re.compile(r'\[\[ja:', re.IGNORECASE)
ALREADY_RE = re.compile(re.escape(f"[[Category:{TARGET_CAT}]]"), re.IGNORECASE)


def ensure_target_category(site, dry_run):
    page = site.pages[f"Category:{TARGET_CAT}"]
    if not page.exists:
        content = (
            f"Categories in this tracking category have no [[{{{{wikidata link}}}}]] "
            f"but do have a Japanese interwiki link ([[ja:...]]) in their wikitext. "
            f"The ja: link can be used to look up the corresponding jawiki category "
            f"and retrieve its Wikidata QID.\n\n"
            f"[[Category:Categories missing Wikidata]]"
        )
        if dry_run:
            print(f"DRY RUN: would create Category:{TARGET_CAT}")
        else:
            page.save(content, summary="Bot: create tracking category for missing-Wikidata categories with ja: interwikis")
            print(f"Created: Category:{TARGET_CAT}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="JaInterwikiTaggerBot/1.0 (User:EmmaBot; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    ensure_target_category(site, args.dry_run)

    source = site.categories[SOURCE_CAT]
    cats = [p for p in source if p.namespace == 14]
    print(f"Found {len(cats)} categories missing Wikidata\n")

    tagged = skipped = errors = 0

    for i, cat_page in enumerate(cats, 1):
        cat_name = cat_page.name.removeprefix("Category:")
        try:
            text = cat_page.text()
        except Exception as e:
            print(f"[{i}/{len(cats)}] ERROR reading {cat_name}: {e}")
            errors += 1
            continue

        if not JA_RE.search(text):
            skipped += 1
            continue

        if ALREADY_RE.search(text):
            print(f"[{i}/{len(cats)}] SKIP (already tagged): {cat_name}")
            skipped += 1
            continue

        new_text = text.rstrip() + f"\n[[Category:{TARGET_CAT}]]"

        if args.dry_run:
            print(f"[{i}/{len(cats)}] DRY RUN: would tag {cat_name}")
            tagged += 1
        else:
            try:
                cat_page.save(new_text, summary=f"Bot: tag with [[Category:{TARGET_CAT}]] (has ja: interwiki, no Wikidata)")
                print(f"[{i}/{len(cats)}] TAGGED: {cat_name}")
                tagged += 1
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"[{i}/{len(cats)}] ERROR: {cat_name}: {e}")
                errors += 1

    print(f"\n{'='*60}")
    print(f"Done. Tagged: {tagged} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
