"""
resolve_missing_wikidata_categories.py
=======================================
For every category in Category:Categories_missing_wikidata:

  1. Detect language from name (CJK → Japanese Wikipedia, Latin → English Wikipedia).
  2. Query enwiki or jawiki for the matching Category page's wikibase_item (QID).
  3. If a QID is found, look up Q{QID} on shintowiki:

     Case A — Q page doesn't exist yet:
       - Create Q{QID} as #REDIRECT [[Category:ThisCategory]]
       - Add {{wikidata link|Q...}} to the category page

     Case B — Q page redirects to THIS category:
       - Add {{wikidata link|Q...}} to the category page (Q page already set up)

     Case C — Q page redirects to a DIFFERENT (Latin/English) category:
       - Merge: recategorize all members of this category to the English one
       - Redirect this category to the English one
       (Same logic as merge_japanese_named_categories.py)

     Case D — Q page is a disambiguation list (multiple categories):
       - Skip (handled by resolve_duplicated_qid_categories.py)

  4. If no QID found on Wikipedia → skip.

Run dry-run first:
    python resolve_missing_wikidata_categories.py --dry-run
"""

import re
import time
import io
import sys
import argparse
import mwclient
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL    = "shinto.miraheze.org"
WIKI_PATH   = "/w/"
USERNAME    = "EmmaBot"
PASSWORD    = "[REDACTED_SECRET_1]"
THROTTLE    = 1.5
WD_THROTTLE = 0.5   # between Wikipedia API calls

SOURCE_CAT  = "Categories_missing_wikidata"
WP_UA       = "ShintowikiBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

REDIRECT_RE   = re.compile(r'#REDIRECT\s*\[\[Category:([^\]]+)\]\]', re.IGNORECASE)
WIKIDATA_RE   = re.compile(r'\{\{wikidata[_ ]link\|?\s*(Q\d+)', re.IGNORECASE)
CAT_TAG_RE    = re.compile(r'(\[\[Category:[^\]]+\]\])', re.IGNORECASE)


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


def get_qid_from_wikipedia(cat_name):
    """Query enwiki or jawiki for the QID of Category:cat_name.
    Tries the primary language first (ja for CJK names, en for Latin),
    then falls back to the other if not found."""
    primary = "ja" if is_cjk(cat_name) else "en"
    fallback = "en" if primary == "ja" else "ja"
    for lang in (primary, fallback):
        try:
            r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", params={
                "action": "query", "format": "json",
                "prop": "pageprops",
                "titles": f"Category:{cat_name}",
            }, headers={"User-Agent": WP_UA}, timeout=10)
            pages = r.json()["query"]["pages"]
            for page in pages.values():
                qid = page.get("pageprops", {}).get("wikibase_item")
                if qid:
                    return qid
        except Exception:
            pass
    return None


def add_wikidata_link(page, qid, dry_run):
    """Insert {{wikidata link|QXXX}} into the category page text."""
    text = page.text()
    if WIKIDATA_RE.search(text):
        print(f"    SKIP add (already has wikidata link): {page.name}")
        return False
    # Insert before first [[Category:...]] tag, or append at end
    m = CAT_TAG_RE.search(text)
    if m:
        insert_pos = m.start()
        new_text = text[:insert_pos] + f"{{{{wikidata link|{qid}}}}}\n" + text[insert_pos:]
    else:
        new_text = text.rstrip() + f"\n{{{{wikidata link|{qid}}}}}\n"
    if dry_run:
        print(f"    DRY RUN: would add {{{{wikidata link|{qid}}}}} to {page.name}")
        return True
    try:
        page.save(new_text, summary=f"Bot: add {{{{wikidata link|{qid}}}}} (found via Wikipedia API)")
        print(f"    ADDED wikidata link: {page.name} → {qid}")
        return True
    except Exception as e:
        print(f"    ERROR adding wikidata link to {page.name}: {e}")
        return False


def recategorize_members(site, from_cat, to_cat, dry_run):
    """Move all members of from_cat to to_cat."""
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
            try:
                page.save(new_text, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging into English equivalent)")
                print(f"      RECATEGORIZED: {page.name}")
            except Exception as e:
                if "editconflict" in str(e).lower():
                    print(f"      CONFLICT on {page.name}, retrying...")
                    time.sleep(5)
                    try:
                        fresh = page.text()
                        fresh_new = pattern.sub(f'[[Category:{to_cat}]]', fresh)
                        if fresh_new != fresh:
                            page.save(fresh_new, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging into English equivalent)")
                            print(f"      RECATEGORIZED (retry): {page.name}")
                        else:
                            print(f"      SKIP (already moved on retry): {page.name}")
                    except Exception as e2:
                        print(f"      ERROR (retry failed): {page.name}: {e2}")
                else:
                    print(f"      ERROR: {page.name}: {e}")
            time.sleep(THROTTLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="MissingWikidataBot/1.0 (User:EmmaBot; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    source = site.categories[SOURCE_CAT]
    cats = [p for p in source if p.namespace == 14]
    print(f"Found {len(cats)} categories missing Wikidata\n")

    if args.limit:
        cats = cats[:args.limit]
        print(f"(Limited to first {args.limit})\n")

    linked = merged = created = skipped = errors = 0

    for i, cat_page in enumerate(cats, 1):
        cat_name = cat_page.name.removeprefix("Category:")

        # Skip if already a redirect
        try:
            text = cat_page.text()
        except Exception as e:
            print(f"[{i}/{len(cats)}] ERROR reading {cat_name}: {e}")
            errors += 1
            continue

        if REDIRECT_RE.search(text):
            print(f"[{i}/{len(cats)}] SKIP (already redirect): {cat_name}")
            skipped += 1
            continue

        if WIKIDATA_RE.search(text):
            print(f"[{i}/{len(cats)}] SKIP (already has wikidata link): {cat_name}")
            skipped += 1
            continue

        # Query Wikipedia for QID
        qid = get_qid_from_wikipedia(cat_name)
        time.sleep(WD_THROTTLE)

        if not qid:
            print(f"[{i}/{len(cats)}] SKIP (no QID on Wikipedia): {cat_name}")
            skipped += 1
            continue

        print(f"[{i}/{len(cats)}] {cat_name} → {qid}")

        # Check Q page on shintowiki
        q_page = site.pages[qid]

        if not q_page.exists:
            # Case A: create Q page + add wikidata link
            print(f"  Case A: Q page does not exist — creating + adding link")
            if not args.dry_run:
                try:
                    q_page.save(
                        f"#REDIRECT [[Category:{cat_name}]]",
                        summary=f"Bot: create QID redirect for [[Category:{cat_name}]]"
                    )
                    print(f"  CREATED: {qid} → Category:{cat_name}")
                    time.sleep(THROTTLE)
                except Exception as e:
                    print(f"  ERROR creating {qid}: {e}")
                    errors += 1
                    continue
            else:
                print(f"  DRY RUN: would create {qid} → Category:{cat_name}")
            if add_wikidata_link(cat_page, qid, args.dry_run):
                time.sleep(THROTTLE)
                created += 1
            continue

        try:
            q_text = q_page.text()
        except Exception as e:
            print(f"  ERROR reading {qid}: {e}")
            errors += 1
            continue

        redir_m = REDIRECT_RE.search(q_text)

        if not redir_m:
            # Case D: disambiguation or something else
            print(f"  Case D: SKIP ({qid} is not a simple redirect)")
            skipped += 1
            continue

        target = redir_m.group(1).strip()

        if target.lower() == cat_name.lower():
            # Case B: Q page already points to this category
            print(f"  Case B: Q page already points to this category — adding link")
            if add_wikidata_link(cat_page, qid, args.dry_run):
                time.sleep(THROTTLE)
                linked += 1
        elif not is_cjk(target):
            # Case C: Q page points to a different English category — merge
            print(f"  Case C: MERGE {cat_name} → {target}")
            if args.dry_run:
                cat_obj = site.categories[cat_name]
                count = sum(1 for _ in cat_obj)
                print(f"  DRY RUN: would recategorize {count} members, redirect category")
                merged += 1
                continue
            recategorize_members(site, cat_name, target, dry_run=False)
            try:
                cat_page.save(
                    f"#REDIRECT [[Category:{target}]]",
                    summary=f"Bot: merge into English equivalent [[Category:{target}]]"
                )
                print(f"  REDIRECTED: Category:{cat_name} → Category:{target}")
                time.sleep(THROTTLE)
                merged += 1
            except Exception as e:
                print(f"  ERROR redirecting category: {e}")
                errors += 1
        else:
            # Q page points to another CJK category — unusual, skip
            print(f"  SKIP (target is also CJK): {target}")
            skipped += 1

    print(f"\n{'='*60}")
    print(f"Done. Linked: {linked} | Created: {created} | Merged: {merged} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
