#!/usr/bin/env python3
"""
tag_untranslated_japanese.py
=============================
Walks all mainspace (ns 0) pages and detects pages containing
untranslated Japanese text (hiragana, katakana, or CJK ideographs
outside of template parameters, interwiki links, and other expected
contexts).

Pages are tagged with bucketed categories based on the count of
Japanese characters found:
  [[Category:Pages with 50+ untranslated japanese characters]]
  [[Category:Pages with 100+ untranslated japanese characters]]
  [[Category:Pages with 150+ untranslated japanese characters]]
  ... up to 5000+

Also removes the old [[Category:Pages with untranslated japanese content]]
tag if present.

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
THROTTLE = 2.5

STATE_FILE = os.path.join(os.path.dirname(__file__), "tag_untranslated_japanese.state")

USER_AGENT = "JapaneseDetectBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Bucketed thresholds for categorization
THRESHOLDS = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]

# Old category to remove during migration
OLD_CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Pages with untranslated japanese content\s*\]\]\n?',
    re.IGNORECASE,
)

# Matches any of the new bucketed category tags
BUCKET_CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Pages with \d+\+ untranslated japanese characters\s*\]\]\n?',
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
    # Wikidata property sections: == property name (Pxxxx) == ... up to next ==
    re.compile(r'^==\s*[^=]*\(P\d+\)\s*==.*?(?=^==\s*[^=]|\Z)', re.DOTALL | re.MULTILINE),
    # Wikitables {| ... |}
    re.compile(r'\{\|.*?\|\}', re.DOTALL),
    # Template calls — iteratively strip innermost {{...}} to handle deep nesting
    # (applied multiple times via strip_templates())
    # Interwiki links [[ja:...]], [[en:...]], etc.
    re.compile(r'\[\[[a-z]{2,}:[^\]]*\]\]', re.IGNORECASE),
    # HTML comments
    re.compile(r'<!--.*?-->', re.DOTALL),
    # <ref>...</ref> tags (references often contain Japanese sources)
    re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL | re.IGNORECASE),
    # Self-closing <ref ... /> tags
    re.compile(r'<ref[^>]*/>', re.IGNORECASE),
    # <nowiki>...</nowiki>
    re.compile(r'<nowiki>.*?</nowiki>', re.DOTALL | re.IGNORECASE),
    # Category links
    re.compile(r'\[\[\s*Category\s*:[^\]]*\]\]', re.IGNORECASE),
    # File/Image links
    re.compile(r'\[\[\s*(?:File|Image)\s*:[^\]]*\]\]', re.IGNORECASE),
    # Gallery tags
    re.compile(r'<gallery[^>]*>.*?</gallery>', re.DOTALL | re.IGNORECASE),
]

# Innermost template pattern — no braces inside
INNERMOST_TEMPLATE_RE = re.compile(r'\{\{[^{}]*\}\}', re.DOTALL)


def strip_templates(text):
    """Iteratively strip innermost templates to handle arbitrary nesting depth."""
    prev = None
    while prev != text:
        prev = text
        text = INNERMOST_TEMPLATE_RE.sub("", text)
    return text


def count_japanese_chars(text):
    """Count characters that are hiragana, katakana, or CJK ideographs."""
    count = 0
    for ch in text:
        cp = ord(ch)
        # Fast range checks instead of unicodedata.name() lookup
        if (0x3040 <= cp <= 0x309F       # Hiragana
            or 0x30A0 <= cp <= 0x30FF    # Katakana
            or 0x4E00 <= cp <= 0x9FFF    # CJK Unified Ideographs
            or 0x3400 <= cp <= 0x4DBF    # CJK Unified Ideographs Extension A
            or 0xF900 <= cp <= 0xFAFF):  # CJK Compatibility Ideographs
            count += 1
    return count


def count_japanese_after_strip(text):
    """
    Return the count of Japanese characters in the page text after
    removing templates, interwiki links, and other expected contexts.
    """
    stripped = text
    for pattern in STRIP_PATTERNS:
        stripped = pattern.sub("", stripped)
    # Strip templates iteratively to handle deep nesting
    stripped = strip_templates(stripped)
    return count_japanese_chars(stripped)


def bucket_categories(jp_count):
    """Return the list of category tags for the given Japanese char count."""
    cats = []
    for t in THRESHOLDS:
        if jp_count >= t:
            cats.append(f"[[Category:Pages with {t}+ untranslated japanese characters]]")
    return cats


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


def iter_category_members(site, category_name):
    """Yield all page titles in a given category via the categorymembers API."""
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category_name}",
        "cmnamespace": "0",
        "cmlimit": "max",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("categorymembers", []):
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
    parser.add_argument("--category", type=str, default=None,
                        help="Only process pages in this category (e.g. 'Pages with 300+ untranslated japanese characters'). "
                             "Useful for re-bucketing a specific tier with new thresholds. "
                             "Ignores state file — always processes all members.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # When targeting a specific category, skip state tracking — always process all members
    if args.category:
        done = set()
        print(f"Category mode: processing all members of [[Category:{args.category}]]")
    else:
        done = load_state(STATE_FILE) if args.apply else set()
        print(f"State: {len(done)} pages already processed")

    edited = skipped = skipped_interwiki = clean = errors = 0
    checked = 0
    finished_all = True

    if args.category:
        print(f"\n--- Scanning [[Category:{args.category}]] ---")
        page_iter = iter_category_members(site, args.category)
    else:
        print(f"\n--- Scanning mainspace (ns 0) ---")
        page_iter = iter_all_pages(site, 0)

    for title in page_iter:
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

        # Count Japanese characters after stripping expected contexts
        jp_count = count_japanese_after_strip(text)

        # Determine desired bucket categories
        desired_cats = bucket_categories(jp_count)

        # Check what's already on the page
        has_old_cat = bool(OLD_CAT_RE.search(text))
        existing_buckets = set(BUCKET_CAT_RE.findall(text))

        # Build the set of bucket cat strings already present
        existing_bucket_set = set()
        for m in BUCKET_CAT_RE.finditer(text):
            existing_bucket_set.add(m.group(0).rstrip("\n"))

        needs_edit = False
        new_text = text

        # Remove old category tag
        if has_old_cat:
            new_text = OLD_CAT_RE.sub("", new_text)
            needs_edit = True

        # Remove any existing bucket cats that no longer apply
        for m in BUCKET_CAT_RE.finditer(new_text):
            tag = m.group(0).rstrip("\n")
            if tag not in desired_cats:
                needs_edit = True
        if needs_edit or any(c not in existing_bucket_set for c in desired_cats):
            # Strip all existing bucket cats and re-add the correct ones
            new_text = BUCKET_CAT_RE.sub("", new_text)
            needs_edit = True

        if not desired_cats and not needs_edit:
            clean += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        if not desired_cats and needs_edit:
            # Only had old cat to remove, no new cats needed
            new_text = new_text.rstrip() + "\n"
        elif needs_edit:
            new_text = new_text.rstrip() + "\n" + "\n".join(desired_cats) + "\n"

        if not needs_edit:
            clean += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        if not args.apply:
            cat_names = [f"{t}+" for t in THRESHOLDS if jp_count >= t]
            print(f"[{checked}] {title} ({jp_count} chars) DRY RUN: would tag {', '.join(cat_names) or 'remove old'}")
            continue

        try:
            cat_names = [f"{t}+" for t in THRESHOLDS if jp_count >= t]
            summary_detail = f"{jp_count} JP chars" + (f", buckets: {', '.join(cat_names)}" if cat_names else ", removing old tag")
            page.save(
                new_text,
                summary=f"Bot: update Japanese content tags ({summary_detail}) {args.run_tag}",
            )
            edited += 1
            print(f"[{checked}] {title} TAGGED ({jp_count} chars: {', '.join(cat_names) or 'removed old'})")
            append_state(STATE_FILE, title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1
            if args.apply:
                append_state(STATE_FILE, title)

    if finished_all and args.apply and not args.category:
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
