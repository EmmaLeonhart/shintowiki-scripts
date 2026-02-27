"""
History merge script for matched wiki move pairs.

For each pair (A, B) where:
  - A is in Move starting points with {{moved to|B}} (exclusively)
  - B is in Move targets with {{moved from|A}} (exclusively)

Steps:
  1. Save B's content (with {{moved from|A}} removed) into memory
  2. Delete B  →  B's revisions go into the deleted archive
  3. Move A → B's title  →  B's title now has A's history
  4. Edit page at B's title to hold B's cleaned content
  5. Undelete B's old revisions  →  merges both histories at B's title

The result is a single page at B's title with the combined revision history
of both A and B, and B's content (minus the {{moved from}} template).

Pages that link to more than one partner are skipped (must be exclusive pairs).
"""

import os
import mwclient
import re
import time
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
SLEEP     = 1.5

CAT_STARTING = 'Move starting points'
CAT_TARGETS  = 'Move targets'
CAT_ERRORS   = 'move templates that do not link to each other'

TMPL_FROM = re.compile(r'\{\{\s*moved from\s*\|([^|]+?)\s*[|}]', re.IGNORECASE)
TMPL_TO   = re.compile(r'\{\{\s*moved to\s*\|([^|]+?)\s*[|}]',   re.IGNORECASE)

# Matches the full {{moved from|...}} tag (with any trailing newline)
TMPL_FROM_FULL = re.compile(
    r'\{\{\s*moved from\s*\|[^}]*\}\}\s*\n?', re.IGNORECASE
)


def get_csrf_token(site):
    return site.api('query', meta='tokens', type='csrf')['query']['tokens']['csrftoken']


def get_category_pages(site, cat_name):
    titles = set()
    for page in site.categories[cat_name]:
        titles.add(page.name)
    return titles


def build_template_maps(site, all_titles):
    """
    Return (from_map, to_map):
      from_map[page] = [list of {{moved from|X}} arguments]
      to_map[page]   = [list of {{moved to|X}} arguments]
    """
    from_map = {}
    to_map   = {}
    total = len(all_titles)
    for i, title in enumerate(sorted(all_titles), 1):
        text = site.pages[title].text() or ''
        froms = [m.group(1).strip() for m in TMPL_FROM.finditer(text)]
        tos   = [m.group(1).strip() for m in TMPL_TO.finditer(text)]
        if froms:
            from_map[title] = froms
        if tos:
            to_map[title] = tos
        if i % 50 == 0:
            print(f'  ...{i}/{total} pages read')
    return from_map, to_map


def find_exclusive_pairs(from_map, to_map, starting_pages, target_pages):
    """
    Return (pairs, error_pages):
      pairs       = list of (a_title, b_title) exclusive mutual pairs
      error_pages = set of page titles whose templates don't resolve to a mutual pair
    """
    pairs      = []
    good_pages = set()   # pages that are part of a valid pair
    seen_b     = set()

    for a_title, tos in to_map.items():
        if a_title not in starting_pages:
            continue
        if len(tos) != 1:
            continue
        b_title = tos[0]
        if b_title not in target_pages:
            continue
        if b_title in seen_b:
            continue
        froms = from_map.get(b_title, [])
        if len(froms) != 1:
            continue
        if froms[0] == a_title:
            pairs.append((a_title, b_title))
            seen_b.add(b_title)
            good_pages.add(a_title)
            good_pages.add(b_title)

    # An error is specifically when BOTH sides have templates but they contradict each other:
    #   A has {{moved to|B}},  B has {{moved from|C}}  where C ≠ A  →  mismatch
    #   B has {{moved from|A}}, A has {{moved to|C}}   where C ≠ B  →  mismatch
    # Pages where only ONE side has a template are handled by the redlink categories.
    error_pages = set()

    for a_title, tos in to_map.items():
        if a_title not in starting_pages or a_title in good_pages:
            continue
        for b_title in tos:
            froms = from_map.get(b_title, [])
            if not froms:
                continue  # B has no {{moved from|}} — not a contradiction
            for c in froms:
                if c != a_title:
                    error_pages.add(a_title)
                    error_pages.add(b_title)

    for b_title, froms in from_map.items():
        if b_title not in target_pages or b_title in good_pages:
            continue
        for a_title in froms:
            tos = to_map.get(a_title, [])
            if not tos:
                continue  # A has no {{moved to|}} — not a contradiction
            for c in tos:
                if c != b_title:
                    error_pages.add(a_title)
                    error_pages.add(b_title)

    return pairs, error_pages


def tag_errors(site, error_pages, already_errored):
    """Add [[Category:move template errors]] to pages that have unmatched templates."""
    cat_tag = f'[[Category:{CAT_ERRORS}]]'
    tagged = 0
    for title in sorted(error_pages):
        if title in already_errored:
            continue
        page = site.pages[title]
        if not page.exists:
            continue
        text = page.text() or ''
        if cat_tag in text:
            continue
        page.save(text.rstrip() + '\n' + cat_tag + '\n',
                  summary='Bot: Flagging unmatched move template')
        print(f'  Flagged error: {title}')
        tagged += 1
        time.sleep(SLEEP)
    return tagged


def merge_pair(site, a_title, b_title, token):
    print(f'\n  Merging: [[{a_title}]] → [[{b_title}]]')

    # --- 1. Read and clean B's content ---
    b_page   = site.pages[b_title]
    b_content = b_page.text() or ''
    b_cleaned = TMPL_FROM_FULL.sub('', b_content).strip()
    print(f'    [1] Saved B content ({len(b_content)} chars → {len(b_cleaned)} cleaned)')

    # --- 2. Delete B ---
    site.api('delete', title=b_title,
             reason=f'Bot: Merging page history with [[{a_title}]]',
             token=token)
    print(f'    [2] Deleted B: {b_title}')
    time.sleep(SLEEP)

    # --- 3. Move A → B's title ---
    site.api('move', **{
        'from':   a_title,
        'to':     b_title,
        'reason': f'Bot: History merge — combining [[{a_title}]] into [[{b_title}]]',
        'token':  token,
        # leave redirect at A's old title (noredirect absent = redirect created)
    })
    print(f'    [3] Moved A ({a_title}) → {b_title}')
    time.sleep(SLEEP)

    # --- 4. Paste B's cleaned content onto the page now at B's title ---
    site.pages[b_title].save(
        b_cleaned,
        summary=f'Bot: Restoring content after history merge (was [[{a_title}]])'
    )
    print(f'    [4] Restored B content at {b_title}')
    time.sleep(SLEEP)

    # --- 5. Undelete B's archived revisions ---
    site.api('undelete', title=b_title,
             reason=f'Bot: Merging archived history of [[{b_title}]] with [[{a_title}]]',
             token=token)
    print(f'    [5] Undeleted archived revisions of {b_title}')
    time.sleep(SLEEP)

    print(f'    DONE: {b_title} now has merged history from both pages')


def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (EmmaBot@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print(f'Logged in to {WIKI_URL}\n')

    token = get_csrf_token(site)

    print('Fetching category members...')
    starting_pages = get_category_pages(site, CAT_STARTING)
    target_pages   = get_category_pages(site, CAT_TARGETS)
    print(f'  Move starting points : {len(starting_pages)}')
    print(f'  Move targets         : {len(target_pages)}')

    all_titles = starting_pages | target_pages
    print(f'\nReading content for {len(all_titles)} pages...')
    from_map, to_map = build_template_maps(site, all_titles)

    pairs, error_pages = find_exclusive_pairs(from_map, to_map, starting_pages, target_pages)
    print(f'\nFound {len(pairs)} exclusive pairs to merge:')
    for a, b in pairs:
        print(f'  {a}  →  {b}')

    print(f'\nFound {len(error_pages)} pages with unmatched move templates:')
    for t in sorted(error_pages):
        print(f'  {t}')

    # Tag error pages
    already_errored = get_category_pages(site, CAT_ERRORS)
    if error_pages:
        print(f'\nTagging error pages...')
        tag_errors(site, error_pages, already_errored)

    if not pairs:
        print('\nNo pairs to merge.')
        return

    done = errors = 0
    for a_title, b_title in pairs:
        try:
            merge_pair(site, a_title, b_title, token)
            done += 1
            # Refresh token periodically (after every 10 merges)
            if done % 10 == 0:
                token = get_csrf_token(site)
        except Exception as e:
            print(f'    ERROR merging ({a_title} → {b_title}): {e}')
            errors += 1

    print(f'\n{"="*60}')
    print(f'Done! Merged: {done}, Errors: {errors}')


if __name__ == '__main__':
    main()
