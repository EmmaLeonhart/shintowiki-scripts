#!/usr/bin/env python3
"""
enrich_enwiki_categories.py
============================
Enrich categories in [[Category:Emmabot categories with enwiki]] by adding
an enwiki interlanguage link and wikidata link (if available).

Mirror of `enrich_jawiki_categories.py` for the enwiki bucket produced by
`triage_emmabot_categories.py` (which moves categories from
[[Category:Categories autocreated by EmmaBot]] into "with enwiki" /
"without enwiki" buckets based on whether enwiki has a matching
category page).

For each category:
1. Look up the matching Category page on en.wikipedia.org
2. If enwiki page NOT found: tag with
   [[Category:Emmabot enwiki categories false positives]]
3. If enwiki page found but NO wikidata: add [[en:Category:Name]]
   interlanguage link, tag with
   [[Category:Emmabot enwiki categories with only enwiki category and no wikidata]]
4. If enwiki page found WITH wikidata: add [[en:Category:Name]] +
   {{wikidata link|QID}}, tag with
   [[Category:Emmabot enwiki categories with wikidata]]

In all cases, removes [[Category:Emmabot categories with enwiki]].

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

SOURCE_CAT = "Emmabot categories with enwiki"
FALSE_POSITIVE_CAT = "Emmabot enwiki categories false positives"
ENWIKI_ONLY_CAT = "Emmabot enwiki categories with only enwiki category and no wikidata"
ENWIKI_WIKIDATA_CAT = "Emmabot enwiki categories with wikidata"

ENWIKI_API = "https://en.wikipedia.org/w/api.php"
ENWIKI_BATCH_SIZE = 50
WP_UA = "EmmaBot/1.0 (shinto.miraheze.org)"

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Emmabot categories with enwiki\s*\]\]\s*\n?",
    re.IGNORECASE,
)
WIKIDATA_LINK_RE = re.compile(
    r"\{\{\s*wikidata link\s*\|\s*[Qq]\d+\s*\}\}",
    re.IGNORECASE,
)
EN_LINK_RE = re.compile(
    r"\[\[en:[^\]]+\]\]\s*\n?",
    re.IGNORECASE,
)


def check_enwiki_categories_with_wikidata(titles):
    """Check enwiki for each title. Returns dict: title -> (exists, qid_or_none)."""
    results = {}
    for i in range(0, len(titles), ENWIKI_BATCH_SIZE):
        batch = titles[i : i + ENWIKI_BATCH_SIZE]
        query_titles = "|".join(f"Category:{t}" for t in batch)
        try:
            resp = requests.get(
                ENWIKI_API,
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
            print(f"  enwiki API error: {e}")
            for t in batch:
                results[t] = (False, None)
            continue

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            full_title = page.get("title", "")
            bare = full_title[len("Category:"):] if full_title.startswith("Category:") else full_title

            if page.get("missing") is not None:
                results[bare] = (False, None)
                continue

            qid = page.get("pageprops", {}).get("wikibase_item")
            results[bare] = (True, qid)

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
        clients_useragent="EnrichEnwikiCats/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    names = list(iter_source_categories(site))

    if not names:
        print("No categories to process.")
        return

    print(f"Collected {len(names)} categories.\n")

    print("Checking enwiki for categories and wikidata items...")
    enwiki_info = check_enwiki_categories_with_wikidata(names)

    found_count = sum(1 for exists, _ in enwiki_info.values() if exists)
    wd_count = sum(1 for exists, qid in enwiki_info.values() if exists and qid)
    print(f"  {found_count} found on enwiki, {wd_count} with wikidata, {len(names) - found_count} false positives\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        exists, qid = enwiki_info.get(name, (False, None))
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

        new_text = SOURCE_CAT_RE.sub("", text)

        if not exists:
            target_cat = FALSE_POSITIVE_CAT
            summary_tag = "false positive"
        elif qid:
            target_cat = ENWIKI_WIKIDATA_CAT
            summary_tag = f"enwiki + wikidata {qid}"

            if not EN_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n[[en:Category:{name}]]\n"

            if not WIKIDATA_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n{{{{wikidata link|{qid}}}}}\n"
        else:
            target_cat = ENWIKI_ONLY_CAT
            summary_tag = "enwiki only, no wikidata"

            if not EN_LINK_RE.search(new_text):
                new_text = new_text.rstrip() + f"\n[[en:Category:{name}]]\n"

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
                summary=f"Bot: enrich enwiki category ({summary_tag}) {args.run_tag}",
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
