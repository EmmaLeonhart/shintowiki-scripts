"""
move_categories.py
==================
Reads a CSV file of (source, destination) category pairs and performs moves.

For each pair:
  Skip if:
    - Source page does not exist.
    - Source is already a redirect.
    - Source already has {{category move error|...}}.

  Tag if:
    - Source exists AND destination also exists as a real page:
      Prepend {{category move error|DESTINATION}} to source page.

  Move if:
    - Source exists, destination does not exist:
      1. Recategorize all members from source category to destination.
      2. Move source category page to destination (leaves redirect at source).

CSV format (header line required):
    source,destination
    Category:日本語名,Category:English Name

Usage:
    python move_categories.py [--csv PATH] [--apply] [--max-edits N] [--run-tag TEXT]
"""

import os
import re
import time
import io
import sys
import csv
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD  = os.getenv("WIKI_PASSWORD", "")
THROTTLE  = 1.5

REDIRECT_RE   = re.compile(r"^\s*#redirect\b", re.IGNORECASE | re.MULTILINE)
MOVE_ERROR_RE = re.compile(r"\{\{\s*category[ _]move[ _]error\b", re.IGNORECASE)


def recategorize_members(site, from_name, to_name, apply, run_tag, edit_counter, max_edits):
    """Replace [[Category:from_name]] with [[Category:to_name]] on all member pages."""
    cat = site.categories[from_name]
    members = list(cat)
    print(f"    {len(members)} member(s) to recategorize")

    pattern = re.compile(
        r"\[\[Category:" + re.escape(from_name).replace(r"\ ", r"[_ ]") + r"(\|[^\]]*)??\]\]",
        re.IGNORECASE,
    )

    for page in members:
        if edit_counter[0] >= max_edits:
            print("      MAX EDITS reached, stopping member recategorization.")
            return

        text = page.text()
        new_text = pattern.sub(f"[[Category:{to_name}]]", text)
        if new_text == text:
            print(f"      SKIP (tag not found in wikitext): {page.name}")
            continue

        if not apply:
            print(f"      DRY RUN: would recategorize {page.name}")
            continue

        summary = f"Bot: recategorize [[Category:{from_name}]] → [[Category:{to_name}]] {run_tag}".strip()
        try:
            page.save(new_text, summary=summary)
            print(f"      RECATEGORIZED: {page.name}")
            edit_counter[0] += 1
        except Exception as e:
            if "editconflict" in str(e).lower():
                print(f"      CONFLICT on {page.name}, retrying...")
                time.sleep(5)
                try:
                    fresh = page.text()
                    fresh_new = pattern.sub(f"[[Category:{to_name}]]", fresh)
                    if fresh_new != fresh:
                        page.save(fresh_new, summary=summary)
                        print(f"      RECATEGORIZED (retry): {page.name}")
                        edit_counter[0] += 1
                    else:
                        print(f"      SKIP (already moved on retry): {page.name}")
                except Exception as e2:
                    print(f"      ERROR (retry failed): {page.name}: {e2}")
            else:
                print(f"      ERROR: {page.name}: {e}")
        time.sleep(THROTTLE)


def main():
    default_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "category_moves.csv")
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--csv", default=default_csv, help="Path to CSV file of moves")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    parser.add_argument("--max-edits", type=int, default=500, help="Maximum edits to make")
    parser.add_argument("--run-tag", default="", help="Edit summary suffix (GitHub Actions run link)")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="CategoryMoveBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    moves = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            src = row["source"].strip()
            dst = row["destination"].strip()
            if src and dst:
                moves.append((src, dst))

    print(f"Loaded {len(moves)} move(s) from {args.csv}\n")

    edit_counter = [0]
    moved = tagged = skipped = errors = 0

    for i, (src_full, dst_full) in enumerate(moves, 1):
        if edit_counter[0] >= args.max_edits:
            print("MAX EDITS reached, stopping.")
            break

        src_name = src_full.removeprefix("Category:")
        dst_name = dst_full.removeprefix("Category:")

        print(f"[{i}/{len(moves)}] {src_full} → {dst_full}")

        try:
            src_page = site.pages[src_full]
            if not src_page.exists:
                print("  SKIP: source page does not exist")
                skipped += 1
                continue
            src_text = src_page.text()
        except Exception as e:
            print(f"  ERROR reading source: {e}")
            errors += 1
            continue

        if REDIRECT_RE.search(src_text):
            print("  SKIP: source is already a redirect")
            skipped += 1
            continue

        if MOVE_ERROR_RE.search(src_text):
            print("  SKIP: source already has {{category move error}}")
            skipped += 1
            continue

        try:
            dst_page = site.pages[dst_full]
            dst_exists = dst_page.exists
        except Exception as e:
            print(f"  ERROR checking destination: {e}")
            errors += 1
            continue

        if dst_exists:
            # Both source and destination exist — tag source with conflict marker
            print(f"  CONFLICT: destination already exists → adding {{{{category move error|{dst_name}}}}}")
            new_src_text = "{{category move error|" + dst_name + "}}\n" + src_text
            if not args.apply:
                print(f"  DRY RUN: would tag {src_full}")
            else:
                summary = (
                    f"Bot: flag category move conflict, [[Category:{dst_name}]] already exists {args.run_tag}"
                ).strip()
                try:
                    src_page.save(new_src_text, summary=summary)
                    print(f"  TAGGED: {src_full}")
                    edit_counter[0] += 1
                except Exception as e:
                    print(f"  ERROR tagging: {e}")
                    errors += 1
                    continue
                time.sleep(THROTTLE)
            tagged += 1
            continue

        # Destination does not exist — perform the move
        print("  ACTION: recategorize members then move category page")
        recategorize_members(
            site, src_name, dst_name, args.apply, args.run_tag, edit_counter, args.max_edits
        )

        if edit_counter[0] >= args.max_edits:
            print("  MAX EDITS reached after recategorizing members, skipping page move.")
            break

        if not args.apply:
            print(f"  DRY RUN: would move {src_full} → {dst_full}")
        else:
            summary = f"Bot: move untranslated category to English equivalent {args.run_tag}".strip()
            try:
                src_page.move(dst_full, reason=summary, no_redirect=False)
                print(f"  MOVED: {src_full} → {dst_full}")
                edit_counter[0] += 1
            except Exception as e:
                print(f"  ERROR moving page: {e}")
                errors += 1
                continue
            time.sleep(THROTTLE)
        moved += 1

    print(f"\n{'=' * 60}")
    print(f"Done. Moved: {moved} | Conflict-tagged: {tagged} | Skipped: {skipped} | Errors: {errors}")
    print(f"Total edits made: {edit_counter[0]}")


if __name__ == "__main__":
    main()
