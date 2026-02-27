"""
fix_erroneous_qid_category_links.py
===================================
For pages in Category:Erroneous_qid_category_links:
- If every numbered category link points to the same category page,
  replace page content with a simple redirect to that category.

Default mode is dry-run. Use --apply to save edits.
"""

import argparse
import io
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE = 1.5

SOURCE_CAT = "Erroneous_qid_category_links"

LIST_LINK_RE = re.compile(
    r"^\s*#\s*\[\[\s*:?\s*Category\s*:\s*([^\]|]+)(?:\|[^\]]*)?\s*\]\]\s*$",
    re.IGNORECASE,
)
TRACKING_CAT_RE = re.compile(
    r"^\s*\[\[\s*Category\s*:\s*Erroneous[_ ]qid[_ ]category[_ ]links(?:\|[^\]]*)?\s*\]\]\s*$",
    re.IGNORECASE,
)


def normalize_title(title):
    return " ".join(title.replace("_", " ").split()).casefold()


def parse_candidate(text):
    targets = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LIST_LINK_RE.match(line)
        if m:
            targets.append(" ".join(m.group(1).replace("_", " ").split()))
            continue
        if TRACKING_CAT_RE.match(line):
            continue
        return None
    if not targets:
        return None
    unique = {normalize_title(t) for t in targets}
    if len(unique) != 1:
        return None
    return targets[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process (0 = no limit).")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="ErroneousQidFixBot/1.0 (User:Immanuelle; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    cat = site.categories[SOURCE_CAT]
    processed = fixed = skipped = errors = 0

    for page in cat:
        if args.limit and processed >= args.limit:
            break
        processed += 1
        prefix = f"[{processed}] {page.name}"

        try:
            text = page.text()
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        target = parse_candidate(text)
        if not target:
            print(f"{prefix} SKIP (not a single-target duplicate list)")
            skipped += 1
            continue

        new_text = f"#REDIRECT [[Category:{target}]]\n"
        if text.strip() == new_text.strip():
            print(f"{prefix} SKIP (already redirect)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would redirect to [[Category:{target}]]")
            fixed += 1
            continue

        try:
            page.save(
                new_text,
                summary="Bot: convert single-target erroneous QID category link list into redirect",
            )
            print(f"{prefix} FIXED -> [[Category:{target}]]")
            fixed += 1
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1

        time.sleep(THROTTLE)

    print("\n" + "=" * 60)
    print(f"Processed: {processed}")
    print(f"Fixed:     {fixed}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")


if __name__ == "__main__":
    main()
