#!/usr/bin/env python3
"""
remove_legacy_cat_templates.py
================================
Removes legacy maintenance templates that were introduced by old automated
passes onto category pages and should not be there:

  - {{デフォルトソート:…}}   (Japanese DEFAULTSORT; erroneous automated pass artifact)
  - {{citation needed|…}}    (sourcing tag; not appropriate on category pages)

Iterates all Category: namespace pages using a state file for resumability.
Default mode is dry-run; use --apply to save edits.
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
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
THROTTLE = 1.5
DEFAULT_STATE_FILE = "shinto_miraheze/remove_legacy_cat_templates.state"

# Each pattern strips a specific legacy template and an optional trailing newline.
# These templates are expected to be simple (no nested braces) from automated passes.
STRIP_PATTERNS = [
    # {{デフォルトソート:SomeName}} — Japanese DEFAULTSORT artifact
    re.compile(r"\{\{\s*デフォルトソート\s*:[^\{\}]*\}\}\n?"),
    # {{citation needed}} or {{citation needed|date=…}} — sourcing tag artifact
    re.compile(r"\{\{\s*[Cc]itation\s+[Nn]eeded\s*(?:\|[^\{\}]*)?\}\}\n?"),
]

REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE)


def iter_category_titles(site):
    params = {
        "list": "allpages",
        "apnamespace": 14,
        "aplimit": "max",
        "apfilterredir": "nonredirects",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def load_state(path):
    completed = set()
    if not os.path.exists(path):
        return completed
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                completed.add(s)
    return completed


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def strip_legacy_templates(text):
    for pat in STRIP_PATTERNS:
        text = pat.sub("", text)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=0, help="Max edits to save in this run (0 = no limit).")
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="Path to resume-state file.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="LegacyCatTemplateRemoverBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    completed_titles = load_state(args.state_file) if args.apply else set()
    if args.apply:
        print(f"Loaded {len(completed_titles)} completed titles from state: {args.state_file}")

    processed = edited = skipped = errors = 0

    for title in iter_category_titles(site):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping run.")
            break

        if args.apply and title in completed_titles:
            skipped += 1
            continue

        processed += 1
        page = site.pages[title]
        prefix = f"[{processed}] {title}"

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not text or REDIRECT_RE.match(text):
            skipped += 1
            if args.apply:
                append_state(args.state_file, title)
                completed_titles.add(title)
            continue

        new_text = strip_legacy_templates(text)
        if new_text.rstrip() == text.rstrip():
            skipped += 1
            if args.apply:
                append_state(args.state_file, title)
                completed_titles.add(title)
            continue

        if not args.apply:
            print(f"{prefix} DRY RUN: would strip legacy templates")
            continue

        try:
            page.save(
                new_text,
                summary=(
                    "Bot: remove legacy category-page templates "
                    "({{デフォルトソート}}, {{citation needed}}) "
                    f"{args.run_tag}"
                ),
            )
            edited += 1
            print(f"{prefix} EDITED")
            append_state(args.state_file, title)
            completed_titles.add(title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Processed: {processed} | Edited: {edited} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
