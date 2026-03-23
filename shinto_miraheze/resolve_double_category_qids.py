#!/usr/bin/env python3
"""
resolve_double_category_qids.py
================================
Walks pages in [[Category:Double category qids]].  Each page is a QID
disambiguation listing two or more category links.

For each page, follow redirects on every listed category.  If they ALL
resolve to the same final target, replace the disambiguation page with
a simple #REDIRECT [[FinalTarget]].  Otherwise leave it alone.

Default mode is dry-run.  Use --apply to save edits.
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

SOURCE_CAT = "Double category qids"
REDIRECT_RE = re.compile(r"#REDIRECT\s*\[\[([^\]]+)\]\]", re.IGNORECASE)
# Match [[:Category:...]] or [[:...]] links in numbered list items
LINK_RE = re.compile(r"\[\[:([^\]]+)\]\]")


def normalize_title(title):
    """Normalize a page title for comparison."""
    title = title.split("#")[0]
    title = title.replace("_", " ")
    title = " ".join(title.split())
    return title.strip()


def strip_leading_colon(title):
    """Strip a leading colon from a title (used in category redirects to
    prevent self-categorization, e.g. #REDIRECT [[:Category:X]])."""
    return title.lstrip(":")


def resolve_final_target(site, title, max_depth=10):
    """Follow redirect chain to the final destination.

    Returns the final page title (normalized), or the input title if
    the page is not a redirect or doesn't exist.
    """
    seen = set()
    current = normalize_title(strip_leading_colon(title))

    for _ in range(max_depth):
        key = current.casefold()
        if key in seen:
            return current
        seen.add(key)

        try:
            page = site.pages[current]
            text = page.text() if page.exists else ""
        except Exception:
            return current

        if not text:
            return current

        m = REDIRECT_RE.match(text)
        if m is None:
            return current
        # Strip leading colon — category redirects use [[:Category:X]]
        current = normalize_title(strip_leading_colon(m.group(1)))

    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100, help="Max edits for this run.")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="ResolveDoubleCategoryQids/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    cat = site.categories[SOURCE_CAT]
    pages = [p for p in cat if p.namespace == 0]
    print(f"Found {len(pages)} pages in [[Category:{SOURCE_CAT}]]\n")

    resolved = skipped = errors = 0

    for page in pages:
        if args.max_edits and resolved >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping run.")
            break

        title = page.name
        prefix = f"[{resolved + skipped + errors + 1}] {title}"

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not text:
            print(f"{prefix} SKIP (empty)")
            skipped += 1
            continue

        # Extract all [[:...]] links from the page
        links = LINK_RE.findall(text)
        if len(links) < 2:
            print(f"{prefix} SKIP (fewer than 2 links found)")
            skipped += 1
            continue

        # Resolve each linked category to its final target
        targets = []
        for link in links:
            final = resolve_final_target(site, link)
            targets.append(final)
            print(f"  {link} -> {final}")

        # Check if all resolve to the same target
        normalized_targets = set(t.casefold() for t in targets)
        if len(normalized_targets) > 1:
            print(f"{prefix} SKIP (different targets: {targets})")
            skipped += 1
            continue

        # All go to the same place - turn into a redirect
        final_target = targets[0]
        new_text = f"#REDIRECT [[{final_target}]]"

        if not args.apply:
            print(f"{prefix} DRY RUN: would redirect to [[{final_target}]]")
            resolved += 1
            continue

        try:
            page.save(
                new_text,
                summary=(
                    f"Bot: resolve duplicate QID \u2192 [[{final_target}]] "
                    f"(all entries point to same target) {args.run_tag}"
                ),
            )
            print(f"{prefix} RESOLVED -> [[{final_target}]]")
            resolved += 1
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1

        time.sleep(THROTTLE)

    print("\n" + "=" * 60)
    print(f"Resolved:  {resolved}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")


if __name__ == "__main__":
    main()
