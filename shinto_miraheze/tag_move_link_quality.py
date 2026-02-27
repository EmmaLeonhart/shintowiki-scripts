"""
Check move template link quality and add maintenance categories:

  {{moved from|X}}  → target X doesn't exist    → [[Category:moved from a redlink]]
  {{moved to|X}}    → target X doesn't exist    → [[Category:moved to a redlink]]
  {{moved from|X}}  → target X exists but isn't a redirect
                                                  → [[Category:moved from a non-redirect]]

Pages already in those categories are skipped.
"""

import mwclient
import time
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'EmmaBot'
PASSWORD = '[REDACTED_SECRET_1]'
SLEEP = 1.5

CAT_STARTING     = 'Move starting points'
CAT_TARGETS      = 'Move targets'
CAT_FROM_RED     = 'moved from a redlink'
CAT_TO_RED       = 'moved to a redlink'
CAT_FROM_NONREDIR = 'moved from a non-redirect'

TMPL_FROM = re.compile(r'\{\{\s*moved from\s*\|([^|]+?)\s*[|}]', re.IGNORECASE)
TMPL_TO   = re.compile(r'\{\{\s*moved to\s*\|([^|]+?)\s*[|}]',   re.IGNORECASE)


def get_category_pages(site, cat_name):
    """Return a set of page titles from a category (all namespaces)."""
    titles = set()
    cat = site.categories[cat_name]
    for page in cat:
        titles.add(page.name)
    return titles


def batch_page_info(site, titles):
    """
    Return dict {title: {'exists': bool, 'redirect': bool}} for a list of titles.
    Uses the API in batches of 50.

    IMPORTANT: do NOT pass redirects= to the API call. In MediaWiki, the
    'redirects' flag is a presence-only toggle — passing redirects=False still
    sends the parameter and causes redirects to be followed, which means the
    API returns info about the *destination* page instead of the redirect itself,
    breaking title lookups and making every redirect look like a missing page.
    """
    info = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i+50]
        # No 'redirects' param → API returns the actual redirect page info, not dest
        result = site.api('query', prop='info', titles='|'.join(batch))
        query  = result.get('query', {})

        # Build reverse map: normalized/resolved title → original requested title
        title_map = {t: t for t in batch}
        for norm in query.get('normalized', []):
            title_map[norm['to']] = title_map.get(norm['from'], norm['from'])
        # (we intentionally do NOT process query.get('redirects') — we want the
        #  redirect page itself, not its destination)

        for page_data in query.get('pages', {}).values():
            returned_title  = page_data['title']
            original_title  = title_map.get(returned_title, returned_title)
            exists      = 'missing' not in page_data
            is_redirect = 'redirect' in page_data
            info[original_title] = {'exists': exists, 'redirect': is_redirect}
    return info


def add_categories(page, cats_to_add, existing_text):
    """Append missing category tags to page text. Returns new text or None if nothing added."""
    text = existing_text
    added = []
    for cat in cats_to_add:
        tag = f"[[Category:{cat}]]"
        if tag not in text:
            text = text.rstrip() + "\n" + tag + "\n"
            added.append(cat)
    if not added:
        return None, []
    return text, added


def main():
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (EmmaBot@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL}\n")

    print("Fetching category members...")
    starting_pages = get_category_pages(site, CAT_STARTING)
    target_pages   = get_category_pages(site, CAT_TARGETS)
    already_from_red      = get_category_pages(site, CAT_FROM_RED)
    already_to_red        = get_category_pages(site, CAT_TO_RED)
    already_from_nonredir = get_category_pages(site, CAT_FROM_NONREDIR)

    print(f"  Move starting points      : {len(starting_pages)}")
    print(f"  Move targets              : {len(target_pages)}")
    print(f"  Already in 'from redlink' : {len(already_from_red)}")
    print(f"  Already in 'to redlink'   : {len(already_to_red)}")
    print(f"  Already in 'from non-redir': {len(already_from_nonredir)}")

    # --- Parse all template arguments ---
    # from_map:  {page_title: [linked_titles]} for pages with {{moved from|}}
    # to_map:    {page_title: [linked_titles]} for pages with {{moved to|}}
    from_map = {}
    to_map   = {}

    all_pages = starting_pages | target_pages
    print(f"\nFetching content for {len(all_pages)} pages...")

    linked_titles = set()  # all titles referenced in templates (to batch-check)

    for i, title in enumerate(sorted(all_pages), 1):
        page = site.pages[title]
        text = page.text() or ""

        froms = [m.group(1).strip() for m in TMPL_FROM.finditer(text)]
        tos   = [m.group(1).strip() for m in TMPL_TO.finditer(text)]

        if froms:
            from_map[title] = froms
            linked_titles.update(froms)
        if tos:
            to_map[title] = tos
            linked_titles.update(tos)

        if i % 50 == 0:
            print(f"  ...{i}/{len(all_pages)} pages read")

    print(f"  Found {len(from_map)} pages with {{{{moved from}}}}, "
          f"{len(to_map)} with {{{{moved to}}}}")
    print(f"  Checking {len(linked_titles)} linked titles via API...")

    page_info = batch_page_info(site, linked_titles)

    # --- Determine what categories each page needs ---
    # needs[title] = set of category names to add
    needs = {}

    for title, linked in from_map.items():
        for linked_title in linked:
            info = page_info.get(linked_title, {'exists': False, 'redirect': False})
            if not info['exists']:
                needs.setdefault(title, set()).add(CAT_FROM_RED)
            elif not info['redirect']:
                needs.setdefault(title, set()).add(CAT_FROM_NONREDIR)

    for title, linked in to_map.items():
        for linked_title in linked:
            info = page_info.get(linked_title, {'exists': False, 'redirect': False})
            if not info['exists']:
                needs.setdefault(title, set()).add(CAT_TO_RED)

    # Remove categories already applied
    for title in list(needs.keys()):
        if title in already_from_red:
            needs[title].discard(CAT_FROM_RED)
        if title in already_to_red:
            needs[title].discard(CAT_TO_RED)
        if title in already_from_nonredir:
            needs[title].discard(CAT_FROM_NONREDIR)
        if not needs[title]:
            del needs[title]

    print(f"\n{len(needs)} pages need category updates:")
    for title, cats in sorted(needs.items()):
        print(f"  {title}")
        for c in cats:
            print(f"    + [[Category:{c}]]")

    if not needs:
        print("Nothing to do.")
        return

    # --- Apply edits ---
    done = skipped = errors = 0
    total = len(needs)

    for i, (title, cats) in enumerate(sorted(needs.items()), 1):
        print(f"\n[{i}/{total}] {title}")
        page = site.pages[title]
        if not page.exists:
            print("  SKIP - page does not exist")
            skipped += 1
            continue

        text = page.text() or ""
        new_text, added = add_categories(page, cats, text)
        if new_text is None:
            print("  SKIP - all categories already present")
            skipped += 1
            continue

        summary = "Bot: Tagging move link quality (" + ", ".join(added) + ")"
        try:
            page.save(new_text, summary=summary)
            print(f"  SAVED: {added}")
            done += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

        time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"Done! Saved: {done}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
