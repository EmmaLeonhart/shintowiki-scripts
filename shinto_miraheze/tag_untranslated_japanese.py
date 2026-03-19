#!/usr/bin/env python3
"""
tag_untranslated_japanese.py
=============================
Walks all mainspace (ns 0) pages and detects pages containing
untranslated Japanese text (hiragana, katakana, or CJK ideographs
outside of template parameters, interwiki links, and other expected
contexts).

Pages with significant Japanese content are tagged with
[[Category:Pages with untranslated japanese content]].

* Stateful — tracks processed pages in a .state file so it can resume
  across pipeline runs.
* Processes up to --max-edits pages per run (default 100).
* When all pages have been processed, the state file resets so the
  next run starts a fresh sweep.

Default mode is dry-run. Use --apply to actually edit.
"""

import argparse
import io
import os
import re
import sys
import time
import unicodedata

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 1.5

STATE_FILE = os.path.join(os.path.dirname(__file__), "tag_untranslated_japanese.state")

TARGET_CAT = "Pages with untranslated japanese content"
CAT_TAG = f"[[Category:{TARGET_CAT}]]"

USER_AGENT = "JapaneseDetectBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Matches any existing category tag for our target
TARGET_CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Pages with untranslated japanese content\s*\]\]',
    re.IGNORECASE,
)

REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)

# Interwiki-prefixed pages sitting in mainspace
INTERWIKI_RE = re.compile(r'^[A-Za-z]{2,}:')

# Known local namespace prefixes (NOT interwiki prefixes)
LOCAL_NS_PREFIXES = (
    "Category:", "Template:", "Module:", "Help:", "Talk:", "User:",
    "File:", "MediaWiki:", "Shinto Wiki:", "Wikipedia:",
    "User talk:", "Template talk:", "Category talk:", "File talk:",
    "Help talk:", "Module talk:", "MediaWiki talk:",
)

# ─── JAPANESE DETECTION ────────────────────────────────────

# Patterns to strip before checking for Japanese text.
# These are contexts where Japanese is expected/acceptable.
STRIP_PATTERNS = [
    # Template calls (entire {{...}} including nested)
    # We use a non-greedy approach and handle one level of nesting
    re.compile(r'\{\{[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}', re.DOTALL),
    # Interwiki links [[ja:...]], [[en:...]], etc.
    re.compile(r'\[\[[a-z]{2,}:[^\]]*\]\]', re.IGNORECASE),
    # HTML comments
    re.compile(r'<!--.*?-->', re.DOTALL),
    # <ref>...</ref> tags (references often contain Japanese sources)
    re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL | re.IGNORECASE),
    # <nowiki>...</nowiki>
    re.compile(r'<nowiki>.*?</nowiki>', re.DOTALL | re.IGNORECASE),
    # Category links
    re.compile(r'\[\[\s*Category\s*:[^\]]*\]\]', re.IGNORECASE),
    # File/Image links
    re.compile(r'\[\[\s*(?:File|Image)\s*:[^\]]*\]\]', re.IGNORECASE),
]

# Minimum number of Japanese characters (after stripping) to count as
# "untranslated Japanese content" — avoids false positives from single
# kanji in proper nouns etc.
MIN_JAPANESE_CHARS = 10


def count_japanese_chars(text):
    """Count characters that are hiragana, katakana, or CJK ideographs."""
    count = 0
    for ch in text:
        try:
            name = unicodedata.name(ch, "")
        except ValueError:
            continue
        if any(keyword in name for keyword in (
            "HIRAGANA", "KATAKANA", "CJK UNIFIED", "CJK COMPATIBILITY",
        )):
            count += 1
    return count


def has_significant_japanese(text):
    """
    Return True if the page text contains significant Japanese content
    outside of templates, interwiki links, and other expected contexts.
    """
    stripped = text
    for pattern in STRIP_PATTERNS:
        stripped = pattern.sub("", stripped)

    return count_japanese_chars(stripped) >= MIN_JAPANESE_CHARS


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
        description="Tag mainspace pages with untranslated Japanese content."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max pages to check per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    done = load_state(STATE_FILE) if args.apply else set()
    print(f"State: {len(done)} pages already processed")

    edited = skipped = skipped_interwiki = clean = errors = 0
    checked = 0
    finished_all = True

    print(f"\n--- Scanning mainspace (ns 0) ---")

    for title in iter_all_pages(site, 0):
        if args.max_edits and checked >= args.max_edits:
            print(f"Reached max checks ({args.max_edits}); stopping.")
            finished_all = False
            break

        if title in done:
            continue

        # Skip interwiki-prefixed pages in mainspace
        if INTERWIKI_RE.match(title) and not title.startswith(LOCAL_NS_PREFIXES):
            skipped_interwiki += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        checked += 1

        if checked % 500 == 0:
            print(f"  ... scanned {checked} pages ({edited} tagged, {clean} clean)")

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

        # Already tagged?
        if TARGET_CAT_RE.search(text):
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        # Check for Japanese content
        if not has_significant_japanese(text):
            clean += 1
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
                summary=f"Bot: tag page with untranslated Japanese content {args.run_tag}",
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

    if finished_all and args.apply:
        print("\nAll pages fully processed — clearing state for next cycle.")
        clear_state(STATE_FILE)

    print(f"\n{'='*60}")
    print(f"Checked:    {checked}")
    print(f"Tagged:     {edited}")
    print(f"Clean:      {clean}")
    print(f"Interwiki:  {skipped_interwiki}")
    print(f"Skipped:    {skipped}")
    print(f"Errors:     {errors}")


if __name__ == "__main__":
    main()
