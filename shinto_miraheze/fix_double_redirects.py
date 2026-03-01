#!/usr/bin/env python3
"""
fix_double_redirects.py
=======================
Fixes pages listed on Special:DoubleRedirects by updating each redirect
to point directly to the final target, eliminating intermediate redirects.

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

REDIRECT_RE = re.compile(r"#REDIRECT\s*\[\[([^\]]+)\]\]", re.IGNORECASE)


def normalize_title(title):
    """Normalize a page title for comparison (strip anchor, collapse whitespace)."""
    title = title.split("#")[0]
    title = title.replace("_", " ")
    title = " ".join(title.split())
    return title.casefold()


def iter_double_redirects(site):
    """Yield titles from Special:DoubleRedirects."""
    params = {
        "list": "querypage",
        "qppage": "DoubleRedirects",
        "qplimit": "max",
    }
    while True:
        data = site.api("query", **params)
        entries = data.get("query", {}).get("querypage", {}).get("results", [])
        for entry in entries:
            title = entry.get("title", "")
            if title:
                yield title
        if "continue" in data:
            params.update(data["continue"])
        else:
            break


def get_redirect_target(text):
    """Extract the redirect target from page text, or None if not a redirect."""
    m = REDIRECT_RE.match(text)
    if m:
        return m.group(1).strip()
    return None


def resolve_final_target(site, start_target, max_depth=10):
    """Follow redirect chain from start_target to the final destination.

    Returns the target string of the last redirect in the chain (preserving
    any section anchor it contains), or None if the chain is broken or loops.
    """
    seen = set()
    current = start_target

    for _ in range(max_depth):
        norm = normalize_title(current)
        if norm in seen:
            return None
        seen.add(norm)

        page_title = current.split("#")[0].strip()
        page = site.pages[page_title]
        try:
            text = page.text() if page.exists else ""
        except Exception:
            return None
        if not text:
            return current

        next_target = get_redirect_target(text)
        if next_target is None:
            return current
        current = next_target

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=0, help="Max edits for this run (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="DoubleRedirectFixBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    processed = fixed = skipped = errors = 0

    for title in iter_double_redirects(site):
        if args.max_edits and fixed >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping run.")
            break

        processed += 1
        prefix = f"[{processed}] {title}"

        page = site.pages[title]
        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading page: {e}")
            errors += 1
            continue

        if not page.exists:
            print(f"{prefix} SKIP (missing)")
            skipped += 1
            continue

        current_target = get_redirect_target(text)
        if current_target is None:
            print(f"{prefix} SKIP (not a redirect)")
            skipped += 1
            continue

        final_target = resolve_final_target(site, current_target)
        if final_target is None:
            print(f"{prefix} SKIP (broken or looping redirect chain)")
            skipped += 1
            continue

        if normalize_title(current_target) == normalize_title(final_target):
            print(f"{prefix} SKIP (already points to final target)")
            skipped += 1
            continue

        new_text = REDIRECT_RE.sub(
            f"#REDIRECT [[{final_target}]]",
            text,
            count=1,
        )

        if new_text == text:
            print(f"{prefix} SKIP (no change)")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would redirect to [[{final_target}]] (was [[{current_target}]])")
            fixed += 1
            continue

        try:
            page.save(
                new_text,
                summary=(
                    f"Bot: fix double redirect \u2192 [[{final_target}]] "
                    f"{args.run_tag}"
                ),
            )
            print(f"{prefix} FIXED -> [[{final_target}]] (was [[{current_target}]])")
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
