"""
resolve_duplicated_qid_categories.py
======================================
Processes all Q{QID} pages in Category:Duplicated qid category redirects.

For each Q page with two categories listed:

CASE 1 — one category has a CJK name, one has a Latin name:
  These are the same category under two names (e.g. Category:上野国 and
  Category:Kōzuke Province). The Latin/English name is canonical.
  Actions:
    1. Recategorize all members of the CJK category to the Latin category
    2. Convert the CJK category page to a redirect to the Latin category
    3. Convert the Q page to a simple #REDIRECT [[Category:LatinName]]
    4. (Q page is removed from Category:Duplicated qid category redirects
       automatically since we're replacing the page content)

CASE 2 — both categories have Latin names:
  Likely an error in the original script run. Cannot determine which is
  correct automatically.
  Action:
    Replace [[Category:duplicated qid category redirects]] with
    [[Category:Erroneous qid category links]] on the Q page.
    Leave for manual resolution.

Run dry-run first:
    python resolve_duplicated_qid_categories.py --dry-run
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

DUP_CAT     = "duplicated qid category redirects"
ERROR_CAT   = "Erroneous qid category links"
LIST_RE     = re.compile(r'#\s*\[\[:Category:([^\]]+)\]\]', re.IGNORECASE)


def is_cjk(text):
    for char in text:
        cp = ord(char)
        if any([
            0x4E00 <= cp <= 0x9FFF,   # CJK Unified Ideographs
            0x3040 <= cp <= 0x309F,   # Hiragana
            0x30A0 <= cp <= 0x30FF,   # Katakana
            0x3400 <= cp <= 0x4DBF,   # CJK Extension A
            0xF900 <= cp <= 0xFAFF,   # CJK Compatibility Ideographs
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
        # Replace the category tag (case-insensitive, handle underscores/spaces)
        pattern = re.compile(
            r'\[\[Category:' + re.escape(from_cat).replace(r'\ ', r'[_ ]') + r'(\|[^\]]*)?\]\]',
            re.IGNORECASE
        )
        new_text = pattern.sub(f'[[Category:{to_cat}]]', text)
        if new_text == text:
            print(f"      SKIP (tag not found): {page.name}")
            continue
        if dry_run:
            print(f"      DRY RUN: would recategorize {page.name}")
        else:
            page.save(new_text, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (QID consolidation)")
            print(f"      RECATEGORIZED: {page.name}")
            time.sleep(THROTTLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="DupQidResolverBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    dup_cat = site.categories[DUP_CAT]
    q_pages = [p for p in dup_cat if p.namespace == 0]
    print(f"Found {len(q_pages)} Q pages in Category:{DUP_CAT}\n")

    resolved = errors = skipped = 0

    for i, q_page in enumerate(q_pages, 1):
        q_title = q_page.name
        text = q_page.text()
        cats = LIST_RE.findall(text)

        print(f"[{i}/{len(q_pages)}] {q_title}: {cats}")

        if len(cats) != 2:
            print(f"  SKIP — unexpected number of categories ({len(cats)}), needs manual review")
            skipped += 1
            continue

        cat_a, cat_b = cats
        a_cjk = is_cjk(cat_a)
        b_cjk = is_cjk(cat_b)

        if a_cjk == b_cjk:
            # Both Latin or both CJK — cannot auto-resolve
            print(f"  CASE 2 (both {'CJK' if a_cjk else 'Latin'}) → tagging as erroneous")
            new_text = text.replace(
                f"[[Category:{DUP_CAT}]]",
                f"[[Category:{ERROR_CAT}]]"
            )
            if dry_run := args.dry_run:
                print(f"  DRY RUN: would tag {q_title} as erroneous")
            else:
                q_page.save(new_text, summary=f"Bot: cannot auto-resolve — tagging [[Category:{ERROR_CAT}]]")
                print(f"  TAGGED as erroneous")
                time.sleep(THROTTLE)
            errors += 1

        else:
            # One CJK, one Latin — merge CJK into Latin
            cjk_cat  = cat_a if a_cjk else cat_b
            latin_cat = cat_b if a_cjk else cat_a
            print(f"  CASE 1: CJK={cjk_cat!r}  Latin={latin_cat!r}")

            if args.dry_run:
                print(f"  DRY RUN: would recategorize members, redirect CJK cat, redirect Q page")
                resolved += 1
                continue

            # 1. Recategorize members of CJK category to Latin category
            recategorize_members(site, cjk_cat, latin_cat, args.dry_run)

            # 2. Make CJK category page a redirect to Latin category
            cjk_page = site.pages[f"Category:{cjk_cat}"]
            cjk_page.save(
                f"#REDIRECT [[Category:{latin_cat}]]",
                summary=f"Bot: redirect Japanese-named category to English equivalent (QID consolidation)"
            )
            print(f"  REDIRECTED: Category:{cjk_cat} → Category:{latin_cat}")
            time.sleep(THROTTLE)

            # 3. Convert Q page to simple redirect
            q_page.save(
                f"#REDIRECT [[Category:{latin_cat}]]",
                summary=f"Bot: QID disambiguation resolved — redirect to [[Category:{latin_cat}]]"
            )
            print(f"  Q PAGE RESOLVED: {q_title} → Category:{latin_cat}")
            time.sleep(THROTTLE)

            resolved += 1

    print(f"\n{'='*60}")
    print(f"Done! Resolved: {resolved} | Erroneous (tagged): {errors} | Skipped: {skipped}")


if __name__ == "__main__":
    main()
