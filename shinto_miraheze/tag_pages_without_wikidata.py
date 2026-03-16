#!/usr/bin/env python3
"""
tag_pages_without_wikidata.py
==============================
Walks all pages in mainspace (ns 0), then category space (ns 14), then
template space (ns 10), and checks whether each page contains a
{{wikidata link|...}} template.

Pages that lack the template are tagged with
[[Category:Pages without wikidata]].

* Stateful — tracks processed pages in a .state file so it can resume
  across pipeline runs.
* Processes up to --max-edits pages per run (default 100).
* When all pages in all three namespaces have been processed, the state
  file resets so the next run starts a fresh sweep.

Default mode is dry-run. Use --apply to actually edit.
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
THROTTLE = 1.5

STATE_FILE = os.path.join(os.path.dirname(__file__), "tag_pages_without_wikidata.state")

TARGET_CAT = "Pages without wikidata"
CAT_TAG = f"[[Category:{TARGET_CAT}]]"

USER_AGENT = "WikidataTagBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Matches {{wikidata link|...}} (case-insensitive)
WD_LINK_RE = re.compile(r'\{\{wikidata link\|', re.IGNORECASE)

# Matches any existing [[Category:Pages without wikidata]] tag
TARGET_CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Pages without wikidata\s*\]\]',
    re.IGNORECASE,
)

REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)

# Interwiki-prefixed pages sitting in mainspace — not real local pages.
# mwclient can't read them and they throw KeyError('pages').
INTERWIKI_RE = re.compile(r'^[A-Za-z]{2,}:')

# Known local namespace prefixes (these are NOT interwiki prefixes)
LOCAL_NS_PREFIXES = (
    "Category:", "Template:", "Module:", "Help:", "Talk:", "User:",
    "File:", "MediaWiki:", "Shinto Wiki:", "Wikipedia:",
    "User talk:", "Template talk:", "Category talk:", "File talk:",
    "Help talk:", "Module talk:", "MediaWiki talk:",
)

# Namespaces to process, in order
NAMESPACES = [
    (0, "mainspace"),
    (14, "category"),
    (10, "template"),
]


# ─── STATE ──────────────────────────────────────────────────

def load_state(path):
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                done.add(s)
    return done


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state(path):
    with open(path, "w", encoding="utf-8") as f:
        pass


# ─── HELPERS ────────────────────────────────────────────────

def iter_all_pages(site, namespace):
    """Yield all page titles in a given namespace via the allpages API."""
    params = {
        "list": "allpages",
        "apnamespace": namespace,
        "aplimit": "max",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tag pages without {{wikidata link}} template."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max pages to edit per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    done = load_state(STATE_FILE) if args.apply else set()
    print(f"State: {len(done)} pages already processed")

    edited = skipped = skipped_interwiki = has_wikidata = errors = 0
    checked = 0
    finished_all = True

    for ns, ns_label in NAMESPACES:
        print(f"\n--- Scanning {ns_label} (ns {ns}) ---")

        for title in iter_all_pages(site, ns):
            if args.max_edits and edited >= args.max_edits:
                print(f"Reached max edits ({args.max_edits}); stopping.")
                finished_all = False
                break

            if title in done:
                continue

            # Skip interwiki-prefixed pages in mainspace (e.g. Ar:, Bcl:, Bn:)
            if ns == 0 and INTERWIKI_RE.match(title) and not title.startswith(LOCAL_NS_PREFIXES):
                skipped_interwiki += 1
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            checked += 1

            # Progress logging every 500 pages
            if checked % 500 == 0:
                print(f"  ... scanned {checked} pages ({edited} tagged, {has_wikidata} have wikidata)")

            try:
                page = site.pages[title]
                text = page.text() if page.exists else ""
            except Exception as e:
                print(f"[{checked}] {title} ERROR reading: {e}")
                errors += 1
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            if not page.exists:
                skipped += 1
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            # Skip redirects
            if REDIRECT_RE.search(text):
                skipped += 1
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            # Check for {{wikidata link|...}}
            if WD_LINK_RE.search(text):
                has_wikidata += 1
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            # Already tagged?
            if TARGET_CAT_RE.search(text):
                if args.apply:
                    append_state(STATE_FILE, title)
                continue

            if not args.apply:
                print(f"[{checked}] {title} DRY RUN: would add {CAT_TAG}")
                continue

            try:
                new_text = text.rstrip() + "\n" + CAT_TAG + "\n"
                page.save(
                    new_text,
                    summary=f"Bot: tag page without wikidata link {args.run_tag}",
                )
                edited += 1
                print(f"[{checked}] {title} TAGGED")
                append_state(STATE_FILE, title)
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"[{checked}] {title} ERROR saving: {e}")
                errors += 1
                if args.apply:
                    append_state(STATE_FILE, title)

        else:
            # Inner loop completed without break — continue to next namespace
            continue
        # Inner loop broke (max edits reached) — break outer loop too
        break

    if finished_all and args.apply:
        print("\nAll namespaces fully processed — clearing state for next cycle.")
        clear_state(STATE_FILE)

    print(f"\n{'='*60}")
    print(f"Checked:    {checked}")
    print(f"Tagged:     {edited}")
    print(f"Has WD:     {has_wikidata}")
    print(f"Interwiki:  {skipped_interwiki}")
    print(f"Skipped:    {skipped}")
    print(f"Errors:     {errors}")


if __name__ == "__main__":
    main()
