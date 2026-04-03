#!/usr/bin/env python3
"""
triage_emmabot_categories_secondary.py
=======================================
Third-pass triage for categories that had no enwiki or jawiki match.

Operates on [[Category:Emmabot categories without enwiki or jawiki]] and
applies the following rules:

1. If the category name starts with "Articles" → recategorize to
   [[Category:Bad template generated categories]]
2. If the category has exactly one member whose name matches the category
   name → recategorize to [[Category:Category reflection error]]
3. Otherwise → recategorize to [[Category:Secondary category triage]]

In all cases the original source category tag is removed.

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
THROTTLE = 1.5

SOURCE_CAT = "Emmabot categories without enwiki or jawiki"
BAD_TEMPLATE_CAT = "Bad template generated categories"
REFLECTION_CAT = "Category reflection error"
SECONDARY_CAT = "Secondary category triage"

SOURCE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Emmabot[ _]categories[ _]without[ _]enwiki[ _]or[ _]jawiki\s*\]\]\s*\n?",
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


def get_category_members(site, cat_name):
    """Return a list of (namespace, title) tuples for all members of a category."""
    cat = site.categories[cat_name]
    members = []
    for page in cat.members():
        members.append((page.namespace, page.name))
    return members


def classify_category(name, members):
    """Classify a category into one of the three target buckets.

    Returns (target_cat, tag) where tag is a short description for logging.
    """
    # Rule 1: name starts with "Articles"
    if name.startswith("Articles"):
        return BAD_TEMPLATE_CAT, "bad template"

    # Rule 2: exactly one member with the same name as the category
    if len(members) == 1:
        member_ns, member_name = members[0]
        # The member's full title may or may not have a namespace prefix.
        # Strip "Category:" if present for comparison.
        bare_member = member_name
        if bare_member.startswith("Category:"):
            bare_member = bare_member[len("Category:"):]
        if bare_member == name:
            return REFLECTION_CAT, "reflection"

    # Rule 3: everything else
    return SECONDARY_CAT, "secondary"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100, help="Max pages to process (default 100).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="TriageEmmaBotCatsSecondary/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Collect all category names
    names = list(iter_source_categories(site))

    if not names:
        print("No categories to triage.")
        return

    print(f"Collected {len(names)} categories to triage.\n")

    edited = skipped = errors = 0
    for i, name in enumerate(names, 1):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

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

        # Fetch category members to check reflection rule
        try:
            members = get_category_members(site, name)
        except Exception as e:
            print(f"{prefix} ERROR fetching members: {e}")
            errors += 1
            continue

        target_cat, tag = classify_category(name, members)

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
