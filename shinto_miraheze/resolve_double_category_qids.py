#!/usr/bin/env python3
"""
resolve_double_category_qids.py
================================
Walks pages in [[Category:Double category qids]] (legacy, populated
historically) and [[Category:Currently double category qids]] (new
rolling buffer). Each page is a QID disambiguation listing two or
more category links: e.g.

    # [[:Category:Foo]]
    # [[:Category:Bar]]
    [[Category:Currently double category qids]]

For each page, follow redirects on every listed category and check
whether each resolved title actually exists. The almost-universal
pattern is that one category survived and the other was renamed and
emptied (no redirect was left behind), so most dab pages have
exactly one *existing* target. When that's the case — replace the
whole page with ``#REDIRECT [[ExistingTarget]]``. This also
subsumes the older "all chain to the same target" case.

Pages with multiple distinct *existing* targets need human review.
For those, swap the legacy [[Category:Double category qids]] tag
for [[Category:Currently double category qids]] so the residual
review-needed set is visible separately from historical
accumulation. The legacy category should drain to empty over time.

Default mode is dry-run. Use --apply to save edits.

Bounded scope: ``MAX_PAGES_PER_RUN`` caps per-run page visits so the
job can't hang the cleanup loop the way the un-throttled audit run
did on 2026-04-24 (11+ hours, blocked everything downstream).
``THROTTLE_API`` spaces out reads inside ``resolve_final_target``.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5         # seconds between page.save() calls
THROTTLE_API = 0.3     # seconds between read calls inside resolve_final_target

MAX_PAGES_PER_RUN = 200

LEGACY_CAT = "Double category qids"
PENDING_CAT = "Currently double category qids"
SOURCE_CATS = (LEGACY_CAT, PENDING_CAT)

REDIRECT_RE = re.compile(r"#REDIRECT\s*\[\[([^\]]+)\]\]", re.IGNORECASE)
LINK_RE = re.compile(r"\[\[:([^\]]+)\]\]")
# Excise the legacy tag cleanly when re-tagging multi-target pages.
LEGACY_CAT_RE = re.compile(
    r"\[\[Category:" + re.escape(LEGACY_CAT) + r"\]\]\s*",
    re.IGNORECASE,
)
PENDING_CAT_TAG = f"[[Category:{PENDING_CAT}]]"
CRUD_CAT_TAG = "[[Category:crud categories]]"


def is_japanese_only_category(full_title):
    """True if the category name (the part after 'Category:') contains
    no ASCII letters — i.e. entirely Kanji/Kana/digits/punctuation.
    Used to detect the Japanese-named category in a multi-target dab
    so we can drain it into the corresponding English-named one."""
    parts = full_title.split(":", 1)
    name = parts[1] if len(parts) == 2 else full_title
    return name and not any("a" <= c.lower() <= "z" for c in name)


def normalize_title(title):
    title = title.split("#")[0]
    title = title.replace("_", " ")
    title = " ".join(title.split())
    return title.strip()


def strip_leading_colon(title):
    return title.lstrip(":")


def resolve_final_target(site, title, max_depth=10):
    """Follow the redirect chain. Returns ``(final_title, exists)``.

    ``exists`` is True iff the final terminal page exists on the wiki.
    A non-existent page returns ``exists=False`` — the missing-category
    case this script is built to clear (one of two listed categories
    was renamed and emptied without leaving a redirect).
    """
    seen = set()
    current = normalize_title(strip_leading_colon(title))
    last_exists = False
    for _ in range(max_depth):
        key = current.casefold()
        if key in seen:
            return current, last_exists
        seen.add(key)
        try:
            page = site.pages[current]
            exists = page.exists
            text = page.text() if exists else ""
        except Exception:
            return current, False
        time.sleep(THROTTLE_API)
        last_exists = exists
        if not exists or not text:
            return current, exists
        m = REDIRECT_RE.match(text)
        if m is None:
            return current, True
        current = normalize_title(strip_leading_colon(m.group(1)))
    return current, last_exists


def drain_japanese_into_english(site, jp_titles, en_target, args, edits_so_far):
    """Tag each Japanese-named category as crud and append [[Category:en_target]]
    to every member page. Idempotent: skips pages that already have the
    English category. Returns (edits_made, hit_budget).

    Each save respects the global ``--max-edits`` cap by checking
    ``edits_so_far + edits`` against ``args.max_edits`` before saving.
    """
    edits = 0
    en_tag = f"[[Category:{en_target}]]"
    en_tag_lower = en_tag.lower()

    for jp_full_title in jp_titles:
        # 1. Tag the Japanese-named category page itself as crud.
        jp_cat_page = site.pages[jp_full_title]
        try:
            jp_text = jp_cat_page.text() if jp_cat_page.exists else ""
        except Exception as e:
            print(f"  ERROR reading {jp_full_title}: {e}")
            continue
        if not jp_cat_page.exists:
            print(f"  SKIP drain ({jp_full_title} no longer exists)")
            continue

        if CRUD_CAT_TAG.lower() not in jp_text.lower():
            new_jp_text = (jp_text.rstrip() + "\n" + CRUD_CAT_TAG) if jp_text else CRUD_CAT_TAG
            if args.max_edits and edits_so_far + edits >= args.max_edits:
                return edits, True
            if args.apply:
                try:
                    jp_cat_page.save(
                        new_jp_text,
                        summary=(
                            f"Bot: tag Japanese-named category as crud "
                            f"(draining members into [[:{en_target}]]) {args.run_tag}"
                        ),
                    )
                    print(f"  CRUD-TAGGED [[{jp_full_title}]]")
                    edits += 1
                    time.sleep(THROTTLE)
                except Exception as e:
                    print(f"  ERROR tagging {jp_full_title}: {e}")
            else:
                print(f"  DRY: would crud-tag [[{jp_full_title}]]")
                edits += 1

        # 2. Iterate members and append the English category to each.
        try:
            jp_cat = site.categories[jp_full_title.split(":", 1)[1]]
            members = list(jp_cat)
        except Exception as e:
            print(f"  ERROR enumerating members of {jp_full_title}: {e}")
            continue

        for member in members:
            if args.max_edits and edits_so_far + edits >= args.max_edits:
                return edits, True
            try:
                m_text = member.text() if member.exists else ""
            except Exception as e:
                print(f"  ERROR reading {member.name}: {e}")
                continue
            if not m_text:
                continue
            if en_tag_lower in m_text.lower():
                continue
            new_m_text = m_text.rstrip() + "\n" + en_tag
            if args.apply:
                try:
                    member.save(
                        new_m_text,
                        summary=(
                            f"Bot: add [[Category:{en_target}]] (draining "
                            f"[[{jp_full_title}]]) {args.run_tag}"
                        ),
                    )
                    print(f"  ADDED to [[{member.name}]]")
                    edits += 1
                    time.sleep(THROTTLE)
                except Exception as e:
                    print(f"  ERROR appending to {member.name}: {e}")
            else:
                print(f"  DRY: would add {en_tag} to [[{member.name}]]")
                edits += 1

    return edits, False


def collect_pages(site):
    """Union of pages across both source categories, deduped by title."""
    seen_titles = set()
    pages = []
    for cat_name in SOURCE_CATS:
        try:
            cat = site.categories[cat_name]
            for p in cat:
                if p.namespace != 0:
                    continue
                if p.name in seen_titles:
                    continue
                seen_titles.add(p.name)
                pages.append(p)
        except Exception as e:
            print(f"WARN: failed to read [[Category:{cat_name}]]: {e}")
    return pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Save edits (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max wiki edits for this run.")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL, path=WIKI_PATH,
        clients_useragent="ResolveDoubleCategoryQids/1.1 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    pages = collect_pages(site)
    print(f"Found {len(pages)} unique dab pages across "
          f"[[Category:{LEGACY_CAT}]] and [[Category:{PENDING_CAT}]]\n")

    edits = visited = skipped = errors = 0

    for page in pages:
        if visited >= MAX_PAGES_PER_RUN:
            print(f"Reached MAX_PAGES_PER_RUN ({MAX_PAGES_PER_RUN}); stopping.")
            break
        if args.max_edits and edits >= args.max_edits:
            print(f"Reached max-edits ({args.max_edits}); stopping.")
            break
        visited += 1

        title = page.name
        prefix = f"[{visited}/{len(pages)}] {title}"

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if not text:
            print(f"{prefix} SKIP (empty)")
            skipped += 1
            continue

        links = LINK_RE.findall(text)
        if len(links) < 2:
            print(f"{prefix} SKIP (fewer than 2 links found)")
            skipped += 1
            continue

        resolved = []  # list of (final_title, exists)
        for link in links:
            final, exists = resolve_final_target(site, link)
            resolved.append((final, exists))
            print(f"  {link} -> {final} (exists={exists})")

        # Distinct *existing* targets, casefold-normalized.
        existing_targets = {t.casefold(): t for t, ex in resolved if ex}

        if len(existing_targets) == 1:
            # Either all chain to the same target, or one exists and
            # the rest are missing/redirect-to-it. Redirect to it.
            final_target = next(iter(existing_targets.values()))
            new_text = f"#REDIRECT [[{final_target}]]"

            if not args.apply:
                print(f"{prefix} DRY: would redirect -> [[{final_target}]]")
                edits += 1
                continue
            try:
                page.save(
                    new_text,
                    summary=(
                        f"Bot: resolve duplicate QID -> [[{final_target}]] "
                        f"(only existing target among listed) {args.run_tag}"
                    ),
                )
                print(f"{prefix} RESOLVED -> [[{final_target}]]")
                edits += 1
            except Exception as e:
                print(f"{prefix} ERROR saving: {e}")
                errors += 1
            time.sleep(THROTTLE)
            continue

        if not existing_targets:
            print(f"{prefix} SKIP (no listed target exists)")
            skipped += 1
            continue

        # Multi-target case. If exactly one English-named target plus
        # one or more Japanese-script-only targets exist, drain the
        # Japanese ones into the English one: tag each Japanese cat as
        # crud and append [[Category:English]] to each member. Over
        # subsequent cycles the Japanese cat empties, gets deleted by
        # the unused-categories sweep, and this dab page falls into
        # the single-existing-target branch and gets auto-redirected.
        targets_list = list(existing_targets.values())
        jp_targets = [t for t in targets_list if is_japanese_only_category(t)]
        en_targets = [t for t in targets_list if not is_japanese_only_category(t)]

        if len(en_targets) == 1 and jp_targets:
            en_target = en_targets[0]
            jp_full_titles = [
                t if t.lower().startswith("category:") else f"Category:{t}"
                for t in jp_targets
            ]
            en_target_name = en_target.split(":", 1)[1] if ":" in en_target else en_target
            print(f"{prefix} DRAIN: {jp_full_titles} -> [[Category:{en_target_name}]]")
            drained, hit_budget = drain_japanese_into_english(
                site, jp_full_titles, en_target_name, args, edits
            )
            edits += drained
            if hit_budget:
                print(f"  (hit max-edits during drain; will resume next run)")
                break
            # Fall through to also re-tag the dab page off legacy.

        # Always: move multi-target dabs off the legacy category onto
        # the pending-review buffer so the legacy category drains.
        legacy_present = bool(LEGACY_CAT_RE.search(text))
        pending_present = PENDING_CAT_TAG in text
        if not legacy_present and pending_present:
            print(f"{prefix} SKIP retag (already on pending)")
            skipped += 1
            continue

        new_text = LEGACY_CAT_RE.sub("", text).rstrip()
        if not pending_present:
            new_text = f"{new_text}\n{PENDING_CAT_TAG}"
        if new_text == text:
            print(f"{prefix} SKIP retag (no change)")
            skipped += 1
            continue
        if args.max_edits and edits >= args.max_edits:
            print(f"{prefix} STOP (hit max-edits before retag)")
            break
        targets_str = ", ".join(existing_targets.values())
        if not args.apply:
            print(f"{prefix} DRY: would re-tag (multi-target: {targets_str})")
            edits += 1
            continue
        try:
            page.save(
                new_text,
                summary=(
                    f"Bot: multi-target dab needs review -> move to "
                    f"[[Category:{PENDING_CAT}]] {args.run_tag}"
                ),
            )
            print(f"{prefix} RE-TAGGED (multi-target: {targets_str})")
            edits += 1
        except Exception as e:
            print(f"{prefix} ERROR saving: {e}")
            errors += 1
        time.sleep(THROTTLE)

    print("\n" + "=" * 60)
    print(f"Visited:  {visited}")
    print(f"Edits:    {edits}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
