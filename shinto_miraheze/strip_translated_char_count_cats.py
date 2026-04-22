#!/usr/bin/env python3
"""
strip_translated_char_count_cats.py
====================================
Walks [[Category:Translated pages]] and removes any leftover
``[[Category:Pages with N+ untranslated japanese characters]]`` tags
that ``tag_untranslated_japanese.py`` applied while the page was still
in Japanese. Once a page is in Category:Translated pages the char-count
categories are stale — they describe a state the page no longer has.

One-shot-ish but technically cyclical (pages can be retranslated, or
freshly tagged). State file tracks which titles have been checked so
subsequent runs skip them and find new additions. State resets when
the category iterator is exhausted, giving a fresh sweep on the next
cycle.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (edit cap
per run, default 100), ``--run-tag``.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

STATE_FILE = os.path.join(os.path.dirname(__file__), "strip_translated_char_count_cats.state")

USER_AGENT = "StripTranslatedCharCountCats/1.0 (User:EmmaBot; shinto.miraheze.org)"

SOURCE_CATEGORY = "Translated pages"

# Same bucketed thresholds as tag_untranslated_japanese.py — keep in sync.
THRESHOLDS = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]

# Matches any of the bucketed categories, with optional surrounding
# whitespace and optional trailing newline so removal collapses the line.
_THRESHOLD_ALT = "|".join(str(t) for t in THRESHOLDS)
CHAR_COUNT_CAT_RE = re.compile(
    rf"[ \t]*\[\[\s*Category\s*:\s*Pages with (?:{_THRESHOLD_ALT})\+ untranslated japanese characters\s*\]\][ \t]*\n?",
    re.IGNORECASE,
)


def load_state(path):
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state(path):
    open(path, "w", encoding="utf-8").close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually save edits (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max edits per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Run tag appended to the edit summary.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    done = load_state(STATE_FILE) if args.apply else set()
    print(f"State: {len(done)} titles already checked this cycle")

    category = site.categories[SOURCE_CATEGORY]

    edited = checked = skipped = errors = 0
    finished_all = True

    for page in category:
        if args.apply and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping mid-cycle.")
            finished_all = False
            break
        if not args.apply and edited >= args.max_edits:
            print(f"Reached dry-run limit ({args.max_edits}); stopping.")
            finished_all = False
            break

        title = page.name
        if title in done:
            continue

        checked += 1
        try:
            text = page.text()
        except Exception as e:
            print(f"[{checked}] {title} ERROR reading: {e}")
            errors += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        new_text, n = CHAR_COUNT_CAT_RE.subn("", text)
        if n == 0:
            if args.apply:
                append_state(STATE_FILE, title)
            skipped += 1
            continue

        if not args.apply:
            print(f"[{checked}] {title} DRY RUN: would remove {n} char-count cat(s)")
            edited += 1
            continue

        summary = f"Bot: remove {n} stale untranslated-japanese char-count category tag(s) {args.run_tag}"
        try:
            page.save(new_text, summary=summary)
            edited += 1
            print(f"[{checked}] {title} EDITED: removed {n} cat(s)")
            append_state(STATE_FILE, title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1
            append_state(STATE_FILE, title)

    if finished_all and args.apply:
        print(f"\nCategory sweep complete — clearing state.")
        clear_state(STATE_FILE)

    print(f"\n{'=' * 60}")
    print(f"Checked: {checked}")
    print(f"Edited:  {edited}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    main()
