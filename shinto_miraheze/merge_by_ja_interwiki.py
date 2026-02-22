"""
merge_by_ja_interwiki.py
=========================
Scans Category:Categories missing Wikidata with Japanese interwikis.

Builds a map of jawiki category target → [shintowiki categories that link to it].

For jawiki targets claimed by 2+ shintowiki categories:
  - One CJK + one Latin → merge: recategorize members from CJK into Latin,
    redirect CJK category to Latin.
  - Multiple Latin (no CJK) → tag all with
    [[Category:Jawiki categories with multiple enwiki]] for manual review.

For jawiki targets claimed by exactly one shintowiki category → skip
(handled separately).

Run dry-run first:
    python merge_by_ja_interwiki.py --dry-run
"""

import re
import time
import io
import sys
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL    = "shinto.miraheze.org"
WIKI_PATH   = "/w/"
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_2]"
THROTTLE    = 1.5

SOURCE_CAT  = "Categories missing Wikidata with Japanese interwikis"
MULTI_CAT   = "Jawiki categories with multiple enwiki"

JA_RE       = re.compile(r'\[\[ja:(?:Category:)?([^\]|#\n]+)', re.IGNORECASE)
REDIRECT_RE = re.compile(r'#REDIRECT', re.IGNORECASE)


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
    cat = site.categories[from_cat]
    members = list(cat)
    print(f"    Recategorizing {len(members)} members: {from_cat} → {to_cat}")
    pattern = re.compile(
        r'\[\[Category:' + re.escape(from_cat).replace(r'\ ', r'[_ ]') + r'(\|[^\]]*)??\]\]',
        re.IGNORECASE
    )
    for page in members:
        text = page.text()
        new_text = pattern.sub(f'[[Category:{to_cat}]]', text)
        if new_text == text:
            print(f"      SKIP (tag not found): {page.name}")
            continue
        if dry_run:
            print(f"      DRY RUN: would recategorize {page.name}")
        else:
            try:
                page.save(new_text, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging via shared ja: interwiki)")
                print(f"      RECATEGORIZED: {page.name}")
            except Exception as e:
                if "editconflict" in str(e).lower():
                    print(f"      CONFLICT on {page.name}, retrying...")
                    time.sleep(5)
                    try:
                        fresh = page.text()
                        fresh_new = pattern.sub(f'[[Category:{to_cat}]]', fresh)
                        if fresh_new != fresh:
                            page.save(fresh_new, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging via shared ja: interwiki)")
                            print(f"      RECATEGORIZED (retry): {page.name}")
                        else:
                            print(f"      SKIP (already moved on retry): {page.name}")
                    except Exception as e2:
                        print(f"      ERROR (retry): {page.name}: {e2}")
                else:
                    print(f"      ERROR: {page.name}: {e}")
            time.sleep(THROTTLE)


def ensure_multi_cat(site, dry_run):
    page = site.pages[f"Category:{MULTI_CAT}"]
    if not page.exists:
        if dry_run:
            print(f"DRY RUN: would create Category:{MULTI_CAT}\n")
        else:
            page.save(
                "Categories in this tracking category each have a [[ja:...]] interwiki link "
                "pointing to a jawiki category that is also claimed by at least one other "
                "shintowiki category. Needs manual review to determine which English category "
                "is the correct canonical target.\n\n"
                "[[Category:Categories missing Wikidata]]",
                summary="Bot: create tracking category"
            )
            print(f"Created: Category:{MULTI_CAT}\n")


def tag_multi(site, cat_page, dry_run):
    text = cat_page.text()
    tag = f"[[Category:{MULTI_CAT}]]"
    if tag.lower() in text.lower():
        return
    new_text = text.rstrip() + f"\n{tag}"
    if dry_run:
        print(f"      DRY RUN: would tag {cat_page.name}")
    else:
        try:
            cat_page.save(new_text, summary=f"Bot: tag [[Category:{MULTI_CAT}]] (shared ja: target)")
            print(f"      TAGGED: {cat_page.name}")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"      ERROR tagging {cat_page.name}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="JaInterwikiMergeBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    ensure_multi_cat(site, args.dry_run)

    source = site.categories[SOURCE_CAT]
    cats = [p for p in source if p.namespace == 14]
    print(f"Found {len(cats)} categories to scan\n")

    # Build map: jawiki_target → [(cat_name, page_obj, text), ...]
    print("Reading all pages to build ja: map...")
    ja_map = {}  # jawiki_name → list of (shintowiki_cat_name, page_obj)
    for i, cat_page in enumerate(cats, 1):
        if i % 100 == 0:
            print(f"  Read {i}/{len(cats)}...")
        try:
            text = cat_page.text()
        except Exception:
            continue
        if REDIRECT_RE.search(text):
            continue
        m = JA_RE.search(text)
        if not m:
            continue
        ja_target = m.group(1).strip()
        ja_map.setdefault(ja_target, []).append(
            (cat_page.name.removeprefix("Category:"), cat_page)
        )

    print(f"\nBuilt map: {len(ja_map)} unique jawiki targets\n")

    # Find duplicates
    duplicates = {k: v for k, v in ja_map.items() if len(v) > 1}
    print(f"Jawiki targets with 2+ shintowiki categories: {len(duplicates)}\n")

    merged = tagged = skipped = 0

    for ja_target, entries in duplicates.items():
        names = [name for name, _ in entries]
        cjk_entries   = [(n, p) for n, p in entries if is_cjk(n)]
        latin_entries  = [(n, p) for n, p in entries if not is_cjk(n)]

        if len(cjk_entries) == 1 and len(latin_entries) == 1:
            # Clean merge case
            cjk_name, cjk_page   = cjk_entries[0]
            latin_name, latin_page = latin_entries[0]
            print(f"MERGE: {cjk_name!r} → {latin_name!r}  (ja:{ja_target})")
            if args.dry_run:
                cat_obj = site.categories[cjk_name]
                count = sum(1 for _ in cat_obj)
                print(f"  DRY RUN: would recategorize {count} members, redirect category")
                merged += 1
                continue
            recategorize_members(site, cjk_name, latin_name, dry_run=False)
            try:
                cjk_page.save(
                    f"#REDIRECT [[Category:{latin_name}]]",
                    summary=f"Bot: merge into English equivalent [[Category:{latin_name}]] (shared ja: interwiki)"
                )
                print(f"  REDIRECTED: Category:{cjk_name} → Category:{latin_name}")
                time.sleep(THROTTLE)
                merged += 1
            except Exception as e:
                print(f"  ERROR redirecting: {e}")

        else:
            # Multiple Latin (or other ambiguous case) — tag all for review
            print(f"MULTI ({len(entries)} entries for ja:{ja_target}): {names}")
            for name, page in entries:
                tag_multi(site, page, args.dry_run)
            tagged += len(entries)

    print(f"\n{'='*60}")
    print(f"Done. Merged: {merged} | Tagged as multi: {tagged} | Skipped: {skipped}")


if __name__ == "__main__":
    main()
