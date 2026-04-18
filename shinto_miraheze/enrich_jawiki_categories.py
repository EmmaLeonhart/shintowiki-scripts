#!/usr/bin/env python3
"""
enrich_jawiki_categories.py
============================
Enrich categories in [[Category:Emmabot categories with jawiki]] by adding
a jawiki interlanguage link and wikidata link (if available).

For each category:
1. Look up the matching Category page on ja.wikipedia.org
2. If jawiki page NOT found: tag with [[Category:Emmabot jawiki categories false positives]]
3. If jawiki page found but NO wikidata: add [[ja:カテゴリ:Name]] interlanguage link,
   tag with [[Category:Emmabot jawiki categories with only jawiki category and no wikidata]]
4. If jawiki page found WITH wikidata: add [[ja:カテゴリ:Name]] + {{wikidata link|QID}},
   tag with [[Category:Emmabot jawiki categories with wikidata]]

In all cases, removes [[Category:Emmabot categories with jawiki]].

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

SOURCE_CAT = "Emmabot categories with jawiki"
FALSE_POSITIVE_CAT = "Emmabot jawiki categories false positives"
JAWIKI_ONLY_CAT = "Emmabot jawiki categories with only jawiki category and no wikidata"
JAWIKI_WIKIDATA_CAT = "Emmabot jawiki categories with wikidata"

JAWIKI_API = "https://ja.wikipedia.org/w/api.php"
JAWIKI_BATCH_SIZE = 50
WP_UA = "EmmaBot/1.0 (shinto.miraheze.org)"

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Emmabot categories with jawiki\s*\]\]\s*\n?",
    re.IGNORECASE,
)
WIKIDATA_LINK_RE = re.compile(
    r"\{\{\s*wikidata link\s*\|\s*[Qq]\d+\s*\}\}",
    re.IGNORECASE,
)
JA_LINK_RE = re.compile(
    r"\[\[ja:[^\]]+\]\]\s*\n?",
    re.IGNORECASE,
)


def check_jawiki_categories_with_wikidata(titles):
    """Check jawiki for each title. Returns dict: title -> (exists, qid_or_none)."""
    results = {}
    for i in range(0, len(titles), JAWIKI_BATCH_SIZE):
        batch = titles[i : i + JAWIKI_BATCH_SIZE]
        query_titles = "|".join(f"Category:{t}" for t in batch)
        try:
            resp = requests.get(
                JAWIKI_API,
                params={
                    "action": "query",
                    "titles": query_titles,
                    "prop": "pageprops",
                    "ppprop": "wikibase_item",
                    "format": "json",
                },
                headers={"User-Agent": WP_UA},
                timeout=30,
            )
            data = resp.json()
        except Exception as e:
            print(f"  jawiki API error: {e}")
            for t in batch:
                results[t] = (False, None)
            continue

        # Map normalized titles back to original
        normalized = {}
        for n in data.get("query", {}).get("normalized", []):
            normalized[n["to"]] = n["from"]

        pages = data.get("query", {}).get("pages", {})
        found_titles = set()
        for page in pages.values():
            full_title = page.get("title", "")
            bare = full_title[len("Category:"):] if full_title.startswith("Category:") else full_title

            if page.get("missing") is not None:
                results[bare] = (False, None)
                found_titles.add(bare)
                continue

            qid = page.get("pageprops", {}).get("wikibase_item")
            results[bare] = (True, qid)
            found_titles.add(bare)

        # Mark any batch items not in response as not found
        for t in batch:
            if t not in results:
                results[t] = (False, None)

        time.sleep(0.5)
    return results


def iter_source_categories(site):
    """Yield bare category names from the source category."""
    cat = site.categories[SOURCE_CAT]
    for page in cat.members(namespace=14):
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
        clients_useragent="EnrichJawikiCats/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Collect all category names
    names = list(iter_source_categories(site))

    if not names:
        print("No categories to process.")
        return

    print(f"Collected {len(names)} categories.\n")

    # Batch-check jawiki existence + wikidata
    print("Checking jawiki for categories and wikidata items...")
    jawiki_info = check_jawiki_categories_with_wikidata(names)

    found_count = sum(1 for exists, _ in jawiki_info.values() if exists)
    wd_count = sum(1 for exists, qid in jawiki_info.values() if exists and qid)
    print(f"  {found_count} found on jawiki, {wd_count} with wikidata, {len(names) - found_count} false positives\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        exists, qid = jawiki_info.get(name, (False, None))
        prefix = f"[{i}/{len(names)}] Category:{name}"

        page = site.pages[f"Category:{name}"]
        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (page missing)")
            skipped += 1
            continue

        # Remove source category tag
        new_text = SOURCE_CAT_RE.sub("", text)

        if not exists:
            # False positive — jawiki category doesn't actually exist
            target_cat = FALSE_POSITIVE_CAT
            summary_tag = "false positive"
        elif qid:
            # jawiki exists with wikidata
            target_cat = JAWIKI_WIKIDATA_CAT
            summary_tag = f"jawiki + wikidata {qid}"

            # Add [[ja:カテゴリ:Name]] if not already present
            if not JA_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n[[ja:カテゴリ:{name}]]\n"

            # Add {{wikidata link|QID}} if not already present
            if not WIKIDATA_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n{{{{wikidata link|{qid}}}}}\n"
        else:
            # jawiki exists, no wikidata
            target_cat = JAWIKI_ONLY_CAT
            summary_tag = "jawiki only, no wikidata"

            # Add [[ja:カテゴリ:Name]] if not already present
            if not JA_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n[[ja:カテゴリ:{name}]]\n"

        # Add target category if not already present
        target_re = re.compile(
            rf"\[\[\s*Category\s*:\s*{re.escape(target_cat)}\s*\]\]",
            re.IGNORECASE,
        )
        if not target_re.search(new_text):
            new_text = new_text.rstrip() + f"\n[[Category:{target_cat}]]\n"

        if new_text.rstrip() == text.rstrip():
            print(f"{prefix} SKIP (no change)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: {summary_tag}")
            continue

        try:
            page.save(
                new_text,
                summary=f"Bot: enrich jawiki category ({summary_tag}) {args.run_tag}",
            )
            edited += 1
            print(f"{prefix} EDITED ({summary_tag})")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Processed: {len(names)}")
    print(f"Edited:    {edited}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")


if __name__ == "__main__":
    main()
