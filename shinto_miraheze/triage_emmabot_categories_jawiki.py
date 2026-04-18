#!/usr/bin/env python3
"""
triage_emmabot_categories_jawiki.py
====================================
Second-pass triage for categories that had no enwiki match.

Operates on [[Category:Emmabot categories without enwiki]] and checks
whether a category with the same name exists on Japanese Wikipedia.

For each subcategory:
- If jawiki has a matching category: recategorize to
  [[Category:Emmabot categories with jawiki]]
- If not: recategorize to
  [[Category:Emmabot categories without enwiki or jawiki]]

In both cases the original [[Category:Emmabot categories without enwiki]]
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

SOURCE_CAT = "Emmabot categories without enwiki"
WITH_JAWIKI_CAT = "Emmabot categories with jawiki"
WITHOUT_EITHER_CAT = "Emmabot categories without enwiki or jawiki"

JAWIKI_API = "https://ja.wikipedia.org/w/api.php"
JAWIKI_BATCH_SIZE = 50  # max titles per API query

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Emmabot categories without enwiki\s*\]\]\s*\n?",
    re.IGNORECASE,
)


def check_jawiki_categories(titles):
    """Check which category titles exist on jawiki. Returns set of existing titles."""
    existing = set()
    for i in range(0, len(titles), JAWIKI_BATCH_SIZE):
        batch = titles[i : i + JAWIKI_BATCH_SIZE]
        query_titles = "|".join(f"Category:{t}" for t in batch)
        resp = requests.get(
            JAWIKI_API,
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
            full_title = page.get("title", "")
            if full_title.startswith("Category:"):
                existing.add(full_title[len("Category:"):])
        time.sleep(0.5)  # be polite to jawiki
    return existing


def iter_source_categories(site):
    """Yield bare category names from the source category."""
    cat = site.categories[SOURCE_CAT]
    for page in cat.members(namespace=14):  # 14 = Category namespace
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
        clients_useragent="TriageEmmaBotCatsJawiki/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Collect all category names
    names = list(iter_source_categories(site))

    if not names:
        print("No categories to triage.")
        return

    print(f"Collected {len(names)} categories to triage.\n")

    # Batch-check jawiki existence
    print("Checking jawiki for matching categories...")
    jawiki_existing = check_jawiki_categories(names)
    print(f"  {len(jawiki_existing)} have jawiki matches, {len(names) - len(jawiki_existing)} do not.\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        has_jawiki = name in jawiki_existing
        target_cat = WITH_JAWIKI_CAT if has_jawiki else WITHOUT_EITHER_CAT
        tag = "jawiki" if has_jawiki else "no jawiki"
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
            if new_text == text:
                print(f"{prefix} SKIP (already triaged)")
                skipped += 1
                continue
        else:
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
