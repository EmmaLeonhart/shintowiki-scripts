"""
delete_jawiki_resolution_pages.py
===================================
Deletes all pages in Category:Jawiki_resolution_pages.

Run dry-run first to preview:
    python delete_jawiki_resolution_pages.py --dry-run

Then run for real:
    python delete_jawiki_resolution_pages.py
"""

import io
import sys
import time
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 1.5
CATEGORY  = "Jawiki_resolution_pages"
REASON    = "Bot: deleting jawiki resolution page (unwanted content)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview pages that would be deleted without deleting them")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="DeleteBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    members = list(site.categories[CATEGORY])
    print(f"Found {len(members)} pages in Category:{CATEGORY}\n")

    if not members:
        print("Nothing to delete.")
        return

    deleted = skipped = failed = 0

    for page in members:
        title = page.name
        print(f"  {title}")

        if args.dry_run:
            print(f"    DRY RUN: would delete")
            skipped += 1
            continue

        try:
            if not page.exists:
                print(f"    SKIP (already gone)")
                skipped += 1
                continue

            site.api(
                "delete",
                title=title,
                reason=REASON,
                token=site.get_token("delete"),
            )
            print(f"    DELETED")
            deleted += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

        time.sleep(THROTTLE)

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"Dry run complete. Would delete: {skipped}")
    else:
        print(f"Done. Deleted: {deleted} | Skipped: {skipped} | Failed: {failed}")


if __name__ == "__main__":
    main()
