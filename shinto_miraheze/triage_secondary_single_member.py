#!/usr/bin/env python3
"""
triage_secondary_single_member.py
==================================
Moves categories in [[Category:Secondary category triage]] that have exactly
one member into [[Category:Triaged categories with only one member]].

Default mode is dry-run. Use --apply to save edits.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

SOURCE_CAT = "Secondary category triage"
TARGET_CAT = "Triaged categories with only one member"

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Secondary[ _]category[ _]triage\s*\]\]\s*\n?",
    re.IGNORECASE,
)


def iter_source_categories(site):
    """Yield bare category names from the source category."""
    cat = site.categories[SOURCE_CAT]
    for page in cat.members(namespace=14):  # 14 = Category namespace
        name = page.name
        if name.startswith("Category:"):
            name = name[len("Category:"):]
        yield name


def count_members(site, cat_name):
    """Return the number of members in a category."""
    cat = site.categories[cat_name]
    count = 0
    for _ in cat.members():
        count += 1
        if count > 1:
            return count  # early exit — we only care about exactly 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max pages to process (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL, path=WIKI_PATH,
        clients_useragent="TriageSingleMember/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    names = list(iter_source_categories(site))

    if not names:
        print("No categories in Secondary category triage.")
        return

    print(f"Collected {len(names)} categories to check.\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):

        prefix = f"[{i}/{len(names)}] Category:{name}"

        page = site.pages[f"Category:{name}"]
        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        # Count members
        try:
            member_count = count_members(site, name)
        except Exception as e:
            print(f"{prefix} ERROR counting members: {e}")
            errors += 1
            continue

        if member_count != 1:
            print(f"{prefix} SKIP ({member_count} members)")
            skipped += 1
            continue

        # Replace source category with target category
        new_text = SOURCE_CAT_RE.sub("", text)

        # Check if target already present
        target_pattern = re.compile(
            rf"\[\[\s*Category\s*:\s*{re.escape(TARGET_CAT)}\s*\]\]",
            re.IGNORECASE,
        )
        if target_pattern.search(new_text):
            if new_text == text:
                print(f"{prefix} SKIP (already triaged)")
                skipped += 1
                continue
        else:
            new_text = new_text.rstrip() + f"\n[[Category:{TARGET_CAT}]]\n"

        if new_text == text:
            print(f"{prefix} SKIP (no change)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would move (1 member)")
            continue

        try:
            page.save(
                new_text,
                summary=f"Bot: triage single-member category {args.run_tag}",
            )
            edited += 1
            print(f"{prefix} EDITED (1 member)")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Checked:  {len(names)}")
    print(f"Edited:   {edited}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
