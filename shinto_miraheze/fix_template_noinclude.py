#!/usr/bin/env python3
"""
fix_template_noinclude.py
==========================
Finds templates that have [[Category:...]] or {{wikidata link|...}} placed
outside <noinclude> blocks. When a mainspace page transcludes such a template,
it inherits those categories/wikidata links — which is almost never intended.

The fix: remove the stray tags from their current position and place them
inside a <noinclude> block at the end of the template. Fixed templates are
also tagged with [[Category:Templates fixed with noinclude]].

* Stateful — tracks processed templates in a .state file.
* Processes up to --max-edits templates per run (default 100).
* When all templates have been processed, the state file resets.

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

STATE_FILE = os.path.join(os.path.dirname(__file__), "fix_template_noinclude.state")

USER_AGENT = "NoincludeFixBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

FIXED_CAT = "Templates fixed with noinclude"
FIXED_CAT_TAG = f"[[Category:{FIXED_CAT}]]"

# Patterns to detect stray tags
CATEGORY_RE = re.compile(r'\[\[\s*Category\s*:[^\]]+\]\]', re.IGNORECASE)
WD_LINK_RE = re.compile(r'\{\{wikidata link\|[^}]*\}\}', re.IGNORECASE)
REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)


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

def iter_all_templates(site):
    """Yield all template titles via the allpages API."""
    params = {
        "list": "allpages",
        "apnamespace": 10,
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


def find_noinclude_regions(text):
    """Return list of (start, end) positions for all <noinclude>...</noinclude> blocks."""
    regions = []
    tag_open = re.compile(r'<noinclude\s*>', re.IGNORECASE)
    tag_close = re.compile(r'</noinclude\s*>', re.IGNORECASE)

    for m_open in tag_open.finditer(text):
        start = m_open.start()
        m_close = tag_close.search(text, m_open.end())
        if m_close:
            regions.append((start, m_close.end()))
        else:
            # Unclosed noinclude — treat rest of text as noinclude
            regions.append((start, len(text)))
    return regions


def is_inside_noinclude(pos, regions):
    """Check if a character position falls inside any noinclude region."""
    return any(start <= pos < end for start, end in regions)


def fix_template_text(text):
    """
    Find [[Category:...]] and {{wikidata link|...}} outside <noinclude> blocks.
    Remove them from their current position and collect them into a new
    <noinclude> block at the end.

    Returns (new_text, stray_tags) where stray_tags is the list of tags moved.
    Returns (None, []) if no changes needed.
    """
    regions = find_noinclude_regions(text)

    # Find all category and wikidata link matches outside noinclude
    stray_matches = []  # (start, end, tag_text)

    for m in CATEGORY_RE.finditer(text):
        if not is_inside_noinclude(m.start(), regions):
            # Don't move the "Templates fixed with noinclude" tag we add
            if FIXED_CAT.lower() not in m.group(0).lower():
                stray_matches.append((m.start(), m.end(), m.group(0)))

    for m in WD_LINK_RE.finditer(text):
        if not is_inside_noinclude(m.start(), regions):
            stray_matches.append((m.start(), m.end(), m.group(0)))

    if not stray_matches:
        return None, []

    # Sort by position descending so we can remove from end to start
    stray_matches.sort(key=lambda x: x[0], reverse=True)

    stray_tags = [tag for _, _, tag in stray_matches]
    stray_tags.reverse()  # Back to original order

    # Remove stray tags from text
    new_text = text
    for start, end, _ in stray_matches:
        # Also remove the trailing newline if present
        if end < len(new_text) and new_text[end] == '\n':
            end += 1
        new_text = new_text[:start] + new_text[end:]

    # Clean up any resulting double blank lines
    while '\n\n\n' in new_text:
        new_text = new_text.replace('\n\n\n', '\n\n')

    # Build noinclude block with moved tags + fixed category
    noinclude_content = "\n".join(stray_tags)
    noinclude_block = f"\n<noinclude>\n{noinclude_content}\n{FIXED_CAT_TAG}\n</noinclude>\n"

    new_text = new_text.rstrip() + noinclude_block

    return new_text, stray_tags


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fix templates with categories/wikidata links outside <noinclude>."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max templates to fix per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    done = load_state(STATE_FILE) if args.apply else set()
    print(f"State: {len(done)} templates already processed")

    edited = skipped = errors = 0
    checked = 0
    finished_all = True

    for title in iter_all_templates(site):
        if args.max_edits and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            finished_all = False
            break

        if title in done:
            continue

        checked += 1

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
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        # Skip redirects
        if REDIRECT_RE.search(text):
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        new_text, stray_tags = fix_template_text(text)

        if new_text is None:
            # No stray tags found — nothing to fix
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        tag_summary = ", ".join(stray_tags[:3])
        if len(stray_tags) > 3:
            tag_summary += f" (+{len(stray_tags) - 3} more)"

        if not args.apply:
            print(f"[{checked}] {title} DRY RUN: would move {len(stray_tags)} tag(s): {tag_summary}")
            continue

        try:
            page.save(
                new_text,
                summary=f"Bot: wrap {len(stray_tags)} stray tag(s) in noinclude {args.run_tag}",
            )
            edited += 1
            print(f"[{checked}] {title} FIXED ({len(stray_tags)} tag(s): {tag_summary})")
            append_state(STATE_FILE, title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1
            if args.apply:
                append_state(STATE_FILE, title)

    if finished_all and args.apply:
        print("\nAll templates processed — clearing state for next cycle.")
        clear_state(STATE_FILE)

    print(f"\n{'='*60}")
    print(f"Checked:  {checked}")
    print(f"Fixed:    {edited}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
