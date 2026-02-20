"""
merge_japanese_named_categories.py
=====================================
For every category in Category:Japanese_language_category_names:

  1. Find its {{wikidata link|Q...}} to get the QID.
  2. Look up the Q{QID} mainspace page.
  3. If the Q page is a simple #REDIRECT to a single Latin/English category,
     treat that as the canonical English equivalent.
  4. Recategorize all members from the Japanese category to the English one.
  5. Redirect the Japanese category page to the English one.

Skips if:
  - No {{wikidata link}} found on the page.
  - Q page doesn't exist.
  - Q page is a disambiguation list (multiple categories listed) — those are
    handled by resolve_duplicated_qid_categories.py.
  - Q page redirect target is itself Japanese-named (CJK characters).
  - Japanese category is already a redirect.

Run dry-run first:
    python merge_japanese_named_categories.py --dry-run
"""

import re
import time
import io
import sys
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 1.5

SOURCE_CAT    = "Japanese_language_category_names"
WIKIDATA_RE   = re.compile(r'\{\{wikidata[_ ]link\|?\s*(Q\d+)', re.IGNORECASE)
REDIRECT_RE   = re.compile(r'#REDIRECT\s*\[\[Category:([^\]]+)\]\]', re.IGNORECASE)


def is_cjk(text):
    for char in text:
        cp = ord(char)
        if any([
            0x4E00 <= cp <= 0x9FFF,
            0x3040 <= cp <= 0x309F,
            0x30A0 <= cp <= 0x30FF,
            0x3400 <= cp <= 0x4DBF,
            0xF900 <= cp <= 0xFAFF,
        ]):
            return True
    return False


def recategorize_members(site, from_cat, to_cat, dry_run):
    """Change [[Category:from_cat]] to [[Category:to_cat]] in all members."""
    cat = site.categories[from_cat]
    members = list(cat)
    print(f"    Recategorizing {len(members)} members: {from_cat} → {to_cat}")
    for page in members:
        text = page.text()
        pattern = re.compile(
            r'\[\[Category:' + re.escape(from_cat).replace(r'\ ', r'[_ ]') + r'(\|[^\]]*)??\]\]',
            re.IGNORECASE
        )
        new_text = pattern.sub(f'[[Category:{to_cat}]]', text)
        if new_text == text:
            print(f"      SKIP (tag not found): {page.name}")
            continue
        if dry_run:
            print(f"      DRY RUN: would recategorize {page.name}")
        else:
            page.save(new_text, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging Japanese-named category into English equivalent)")
            print(f"      RECATEGORIZED: {page.name}")
            time.sleep(THROTTLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N categories (0=all)")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="JapaneseCatMergeBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    source = site.categories[SOURCE_CAT]
    ja_cats = [p for p in source if p.namespace == 14]
    print(f"Found {len(ja_cats)} Japanese-named categories\n")

    if args.limit:
        ja_cats = ja_cats[:args.limit]
        print(f"(Limited to first {args.limit})\n")

    merged = skipped = errors = 0

    for i, ja_page in enumerate(ja_cats, 1):
        ja_name = ja_page.name.removeprefix("Category:")

        # Skip if already a redirect
        try:
            text = ja_page.text()
        except Exception as e:
            print(f"[{i}/{len(ja_cats)}] ERROR reading {ja_name}: {e}")
            errors += 1
            continue

        if REDIRECT_RE.search(text):
            print(f"[{i}/{len(ja_cats)}] SKIP (already a redirect): {ja_name}")
            skipped += 1
            continue

        # Find QID
        m = WIKIDATA_RE.search(text)
        if not m:
            print(f"[{i}/{len(ja_cats)}] SKIP (no wikidata link): {ja_name}")
            skipped += 1
            continue

        qid = m.group(1)
        q_page = site.pages[qid]

        if not q_page.exists:
            print(f"[{i}/{len(ja_cats)}] SKIP ({qid} does not exist): {ja_name}")
            skipped += 1
            continue

        try:
            q_text = q_page.text()
        except Exception as e:
            print(f"[{i}/{len(ja_cats)}] ERROR reading {qid}: {e}")
            errors += 1
            continue

        # Check Q page is a simple redirect to one category
        redir_m = REDIRECT_RE.search(q_text)
        if not redir_m:
            print(f"[{i}/{len(ja_cats)}] SKIP ({qid} is not a simple redirect): {ja_name}")
            skipped += 1
            continue

        en_name = redir_m.group(1).strip()

        # Skip if target is also CJK (shouldn't happen but guard anyway)
        if is_cjk(en_name):
            print(f"[{i}/{len(ja_cats)}] SKIP (target is also CJK): {ja_name} → {en_name}")
            skipped += 1
            continue

        # Skip if Japanese and English name are the same category (shouldn't happen)
        if en_name.lower() == ja_name.lower():
            print(f"[{i}/{len(ja_cats)}] SKIP (same name): {ja_name}")
            skipped += 1
            continue

        print(f"[{i}/{len(ja_cats)}] MERGE: {ja_name} → {en_name}  ({qid})")

        if args.dry_run:
            cat_obj = site.categories[ja_name]
            member_count = sum(1 for _ in cat_obj)
            print(f"  DRY RUN: would recategorize {member_count} members, redirect category")
            merged += 1
            continue

        # 1. Recategorize members
        recategorize_members(site, ja_name, en_name, dry_run=False)

        # 2. Redirect the Japanese category to the English one
        ja_page.save(
            f"#REDIRECT [[Category:{en_name}]]",
            summary=f"Bot: merge Japanese-named category into English equivalent [[Category:{en_name}]]"
        )
        print(f"  REDIRECTED: Category:{ja_name} → Category:{en_name}")
        time.sleep(THROTTLE)

        merged += 1

    print(f"\n{'='*60}")
    print(f"Done. Merged: {merged} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
