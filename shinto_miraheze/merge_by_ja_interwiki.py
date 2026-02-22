"""
merge_by_ja_interwiki.py
=========================
Scans Category:Categories missing Wikidata with Japanese interwikis.

Extracts the [[ja:...]] link from each category page to build a map of
jawiki category target → [shintowiki categories that link to it].

For each jawiki target:

  Single shintowiki category:
    - Fetch QID from jawiki API using the ja: link.
    - If found: create Q{QID} redirect + add {{wikidata link|Q...}} (same
      flow as resolve_missing_wikidata_categories.py Case A/B).

  Multiple shintowiki categories → same jawiki target:
    - One CJK + one Latin: merge CJK into Latin (recategorize members,
      redirect CJK → Latin), then add wikidata link to Latin.
    - Two or more Latin (or other ambiguous combos): tag ALL with
      [[Category:jawiki categories with multiple enwiki]] for manual review.

Run dry-run first:
    python merge_by_ja_interwiki.py --dry-run
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
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_2]"
THROTTLE    = 1.5
WD_THROTTLE = 0.5

SOURCE_CAT = "Categories missing Wikidata with Japanese interwikis"
MULTI_CAT  = "jawiki categories with multiple enwiki"
WP_UA      = "ShintowikiBot/1.0 (User:Immanuelle; shinto.miraheze.org)"

JA_LINK_RE  = re.compile(r'\[\[ja:([^\]|]+)', re.IGNORECASE)
REDIRECT_RE = re.compile(r'#REDIRECT\s*\[\[Category:([^\]]+)\]\]', re.IGNORECASE)
WIKIDATA_RE = re.compile(r'\{\{wikidata[_ ]link\|?\s*(Q\d+)', re.IGNORECASE)
CAT_TAG_RE  = re.compile(r'(\[\[Category:[^\]]+\]\])', re.IGNORECASE)


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


def get_qid_from_jawiki(ja_cat_name):
    """Query jawiki for the QID of Category:ja_cat_name."""
    for prefix in ("Category:", "カテゴリ:"):
        try:
            r = requests.get("https://ja.wikipedia.org/w/api.php", params={
                "action": "query", "format": "json",
                "prop": "pageprops",
                "titles": f"{prefix}{ja_cat_name}",
            }, headers={"User-Agent": WP_UA}, timeout=10)
            pages = r.json()["query"]["pages"]
            for page in pages.values():
                qid = page.get("pageprops", {}).get("wikibase_item")
                if qid:
                    return qid
        except Exception:
            pass
    return None


def ensure_multi_cat(site, dry_run):
    page = site.pages[f"Category:{MULTI_CAT}"]
    if not page.exists:
        content = (
            "Categories in this tracking category have a [[ja:...]] interwiki link "
            "that maps to the same jawiki category as one or more other categories "
            "on this wiki. Manual review is needed to determine the canonical category.\n\n"
            "[[Category:Categories missing Wikidata]]"
        )
        if dry_run:
            print(f"DRY RUN: would create Category:{MULTI_CAT}")
        else:
            page.save(content, summary="Bot: create tracking category for jawiki targets with multiple shintowiki categories")
            print(f"Created: Category:{MULTI_CAT}")


def add_wikidata_link(page, qid, dry_run):
    text = page.text()
    if WIKIDATA_RE.search(text):
        print(f"    SKIP add (already has wikidata link): {page.name}")
        return False
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
        page.save(new_text, summary=f"Bot: add {{{{wikidata link|{qid}}}}} (found via jawiki ja: link)")
        print(f"    ADDED wikidata link: {page.name} → {qid}")
        return True
    except Exception as e:
        print(f"    ERROR adding wikidata link to {page.name}: {e}")
        return False


def tag_multi(page, dry_run):
    text = page.text()
    multi_tag = f"[[Category:{MULTI_CAT}]]"
    if multi_tag.lower() in text.lower():
        return False
    new_text = text.rstrip() + f"\n{multi_tag}"
    if dry_run:
        print(f"    DRY RUN: would tag {page.name} with {multi_tag}")
        return True
    try:
        page.save(new_text, summary=f"Bot: tag with [[Category:{MULTI_CAT}]] (ja: link shared with another shintowiki category)")
        print(f"    TAGGED: {page.name}")
        return True
    except Exception as e:
        print(f"    ERROR tagging {page.name}: {e}")
        return False


def recategorize_members(site, from_cat, to_cat, dry_run):
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
                page.save(new_text, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging via shared jawiki target)")
                print(f"      RECATEGORIZED: {page.name}")
            except Exception as e:
                if "editconflict" in str(e).lower():
                    print(f"      CONFLICT on {page.name}, retrying...")
                    time.sleep(5)
                    try:
                        fresh = page.text()
                        fresh_new = pattern.sub(f'[[Category:{to_cat}]]', fresh)
                        if fresh_new != fresh:
                            page.save(fresh_new, summary=f"Bot: recategorize [[Category:{from_cat}]] → [[Category:{to_cat}]] (merging via shared jawiki target)")
                            print(f"      RECATEGORIZED (retry): {page.name}")
                        else:
                            print(f"      SKIP (already moved on retry): {page.name}")
                    except Exception as e2:
                        print(f"      ERROR (retry failed): {page.name}: {e2}")
                else:
                    print(f"      ERROR: {page.name}: {e}")
            time.sleep(THROTTLE)


def handle_single(site, cat_page, cat_name, ja_cat_name, dry_run):
    """Single shintowiki category for this jawiki target — get QID and link."""
    qid = get_qid_from_jawiki(ja_cat_name)
    time.sleep(WD_THROTTLE)
    if not qid:
        print(f"  SKIP (no QID on jawiki for ja:{ja_cat_name})")
        return False

    print(f"  QID: {qid}  (via ja:{ja_cat_name})")

    q_page = site.pages[qid]

    if not q_page.exists:
        if not dry_run:
            try:
                q_page.save(
                    f"#REDIRECT [[Category:{cat_name}]]",
                    summary=f"Bot: create QID redirect for [[Category:{cat_name}]] (via ja:{ja_cat_name})"
                )
                print(f"  CREATED: {qid} → Category:{cat_name}")
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"  ERROR creating {qid}: {e}")
                return False
        else:
            print(f"  DRY RUN: would create {qid} → Category:{cat_name}")
        add_wikidata_link(cat_page, qid, dry_run)
        time.sleep(THROTTLE)
        return True

    try:
        q_text = q_page.text()
    except Exception as e:
        print(f"  ERROR reading {qid}: {e}")
        return False

    redir_m = REDIRECT_RE.search(q_text)
    if not redir_m:
        print(f"  SKIP ({qid} exists but is not a simple redirect)")
        return False

    target = redir_m.group(1).strip()
    if target.lower() == cat_name.lower():
        print(f"  Case B: Q page already points here — adding link")
        add_wikidata_link(cat_page, qid, dry_run)
        time.sleep(THROTTLE)
        return True
    else:
        print(f"  SKIP ({qid} points to different category: {target})")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N singles (0=all)")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="JaInterwikiMergeBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    ensure_multi_cat(site, args.dry_run)

    source = site.categories[SOURCE_CAT]
    all_cats = [p for p in source if p.namespace == 14]
    print(f"Found {len(all_cats)} categories in source\n")

    # --- Phase 1: Build map of jawiki target → shintowiki categories ---
    print("Phase 1: Reading pages to build ja: map...")
    ja_map = {}  # normalized ja category name → [(cat_page, cat_name)]

    for i, cat_page in enumerate(all_cats, 1):
        cat_name = cat_page.name.removeprefix("Category:")
        try:
            text = cat_page.text()
        except Exception as e:
            print(f"  [{i}] ERROR reading {cat_name}: {e}")
            continue

        if REDIRECT_RE.search(text):
            print(f"  [{i}] SKIP (already redirect): {cat_name}")
            continue

        m = JA_LINK_RE.search(text)
        if not m:
            print(f"  [{i}] SKIP (no ja: link): {cat_name}")
            continue

        raw_target = m.group(1).strip()
        # Strip Category:/カテゴリ: prefix from the target
        ja_cat_name = re.sub(r'^カテゴリ:|^Category:', '', raw_target, flags=re.IGNORECASE).strip()

        ja_map.setdefault(ja_cat_name, []).append((cat_page, cat_name))

    singles = {k: v for k, v in ja_map.items() if len(v) == 1}
    multis  = {k: v for k, v in ja_map.items() if len(v) > 1}
    print(f"\nBuilt map: {len(ja_map)} distinct jawiki targets")
    print(f"  Singles: {len(singles)}  |  Multiples (shared target): {len(multis)}\n")

    linked = merged = tagged = skipped = errors = 0

    # --- Phase 2a: Single matches — look up QID and link ---
    print("Phase 2a: Processing single-match categories...")
    singles_list = list(singles.items())
    if args.limit:
        singles_list = singles_list[:args.limit]

    for ja_cat_name, entries in singles_list:
        cat_page, cat_name = entries[0]
        print(f"SINGLE: {cat_name}  (ja:{ja_cat_name})")
        if handle_single(site, cat_page, cat_name, ja_cat_name, args.dry_run):
            linked += 1
        else:
            skipped += 1

    # --- Phase 2b: Multiple matches — merge or tag ---
    print("\nPhase 2b: Processing shared-jawiki-target groups...")
    for ja_cat_name, entries in multis.items():
        names = [n for _, n in entries]
        print(f"MULTI ({len(entries)}): ja:{ja_cat_name}  →  {names}")

        cjk_entries   = [(p, n) for p, n in entries if is_cjk(n)]
        latin_entries = [(p, n) for p, n in entries if not is_cjk(n)]

        if len(cjk_entries) == 1 and len(latin_entries) == 1:
            # Ideal case: one CJK + one Latin → merge CJK into Latin
            cjk_page, cjk_name = cjk_entries[0]
            lat_page, lat_name = latin_entries[0]
            print(f"  MERGE: {cjk_name} → {lat_name}")

            if args.dry_run:
                cat_obj = site.categories[cjk_name]
                count = sum(1 for _ in cat_obj)
                print(f"  DRY RUN: would recategorize {count} members, redirect CJK → Latin, add wikidata link to Latin")
                merged += 1
                continue

            recategorize_members(site, cjk_name, lat_name, dry_run=False)
            try:
                cjk_page.save(
                    f"#REDIRECT [[Category:{lat_name}]]",
                    summary=f"Bot: merge Japanese-named category into English equivalent [[Category:{lat_name}]] (same jawiki target)"
                )
                print(f"  REDIRECTED: Category:{cjk_name} → Category:{lat_name}")
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"  ERROR redirecting {cjk_name}: {e}")
                errors += 1
                continue

            handle_single(site, lat_page, lat_name, ja_cat_name, dry_run=False)
            merged += 1

        else:
            # Multiple Latin, multiple CJK, or 3+ entries — tag all for manual review
            for cat_page, cat_name in entries:
                print(f"  TAG MULTI: {cat_name}")
                if tag_multi(cat_page, args.dry_run):
                    time.sleep(THROTTLE)
                    tagged += 1

    print(f"\n{'='*60}")
    print(f"Done. Linked: {linked} | Merged: {merged} | Tagged (multi): {tagged} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
