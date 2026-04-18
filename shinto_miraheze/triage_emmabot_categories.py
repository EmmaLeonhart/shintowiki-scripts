#!/usr/bin/env python3
"""
triage_emmabot_categories.py
============================
Triages categories in [[Category:Categories autocreated by EmmaBot]] by
checking whether a category with the same name exists on English Wikipedia.

For each subcategory:
- If enwiki has a matching category: recategorize to
  [[Category:Emmabot categories with enwiki]]
- If not: recategorize to
  [[Category:Emmabot categories without enwiki]]

In both cases the original [[Category:Categories autocreated by EmmaBot]]
tag is removed.

Default mode is dry-run. Use --apply to save edits.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

SOURCE_CAT = "Categories autocreated by EmmaBot"
WITH_ENWIKI_CAT = "Emmabot categories with enwiki"
WITHOUT_ENWIKI_CAT = "Emmabot categories without enwiki"

ENWIKI_API = "https://en.wikipedia.org/w/api.php"
ENWIKI_BATCH_SIZE = 50  # max titles per API query

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Categories autocreated by EmmaBot\s*\]\]\s*\n?",
    re.IGNORECASE,
)


def check_enwiki_categories(titles):
    """Check which category titles exist on enwiki. Returns set of existing titles."""
    existing = set()
    # titles are bare names like "Foo", query as "Category:Foo"
    for i in range(0, len(titles), ENWIKI_BATCH_SIZE):
        batch = titles[i : i + ENWIKI_BATCH_SIZE]
        query_titles = "|".join(f"Category:{t}" for t in batch)
        resp = requests.get(
            ENWIKI_API,
            params={
                "action": "query",
                "titles": query_titles,
                "format": "json",
            },
            headers={"User-Agent": "EmmaBot/1.0 (shinto.miraheze.org)"},
            timeout=30,
        )
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("missing") is not None:
                continue
            # Title comes back as "Category:Foo", strip prefix
            full_title = page.get("title", "")
            if full_title.startswith("Category:"):
                existing.add(full_title[len("Category:"):])
        time.sleep(0.5)  # be polite to enwiki
    return existing


def iter_source_categories(site):
    """Yield bare category names from the source category."""
    cat = site.categories[SOURCE_CAT]
    for page in cat.members(namespace=14):  # 14 = Category namespace
        # page.name is "Category:Foo"
        name = page.name
        if name.startswith("Category:"):
            name = name[len("Category:"):]
        yield name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100, help="Max pages to process (default 100).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="TriageEmmaBotCats/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Collect all category names
    names = list(iter_source_categories(site))

    if not names:
        print("No categories to triage.")
        return

    print(f"Collected {len(names)} categories to triage.\n")

    # Batch-check enwiki existence
    print("Checking enwiki for matching categories...")
    enwiki_existing = check_enwiki_categories(names)
    print(f"  {len(enwiki_existing)} have enwiki matches, {len(names) - len(enwiki_existing)} do not.\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        has_enwiki = name in enwiki_existing
        target_cat = WITH_ENWIKI_CAT if has_enwiki else WITHOUT_ENWIKI_CAT
        tag = "enwiki" if has_enwiki else "no enwiki"
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

        # Remove the source category tag
        new_text = SOURCE_CAT_RE.sub("", text)

        # Check if target category is already present
        target_pattern = re.compile(
            rf"\[\[\s*Category\s*:\s*{re.escape(target_cat)}\s*\]\]",
            re.IGNORECASE,
        )
        if target_pattern.search(new_text):
            # Already has target, just remove source if it changed
            if new_text == text:
                print(f"{prefix} SKIP (already triaged)")
                skipped += 1
                continue
        else:
            # Append new category
            new_text = new_text.rstrip() + f"\n[[Category:{target_cat}]]\n"

        if new_text == text:
            print(f"{prefix} SKIP (no change)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would recategorize ({tag})")
            continue

        try:
            page.save(
                new_text,
                summary=f"Bot: triage autocreated category ({tag}) {args.run_tag}",
            )
            edited += 1
            print(f"{prefix} EDITED ({tag})")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Processed: {len(names)}")
    print(f"Edited:    {edited}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")


if __name__ == "__main__":
    main()
