"""resolve_category_wikidata_from_interwiki.py
================================================
Resolve Wikidata for category pages using interwiki links.
================================================

This script:
1. Waits 30 minutes to avoid race conditions
2. Iterates through ALL pages in the Category namespace
3. For each category page:
   - Finds all interwiki links (e.g., [[en:Category:XX]], [[de:Category:YY]])
   - Queries the foreign Wikipedia for the category article
   - Checks if that Wikipedia article has a Wikidata connection
   - Adds {{wikidata link|Q#####}} for each Wikidata item found
   - If multiple Wikidata items exist, adds all of them
   - If no Wikidata found via interwikis, adds [[Category:categories missing wikidata]]
4. Handles all language interwikis
"""

import os
import time
import re
import mwclient
import requests
import sys

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'

# Wait 30 minutes at startup to avoid race conditions
STARTUP_WAIT = 30 * 60  # 30 minutes in seconds

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")


# ─── REGEX PATTERNS ─────────────────────────────────────────

# Match interwiki links like [[ja:XX]], [[en:YY]], etc.
# The interwiki system automatically applies the same namespace (Category), so we just need lang:title
INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')

# Match existing {{wikidata link|Q...}} templates
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|([Qq](\d+))}}')

# Match category links
CATEGORY_RE = re.compile(r'\[\[Category:([^\]]+)\]\]')

# Match [[d:Q...]] wikidata links
WIKIDATA_LINK_RE = re.compile(r'\[\[d:([Qq]\d+)\]\]')


# ─── HELPERS ─────────────────────────────────────────────────

def safe_save(page, text, summary):
    """Attempt Page.save but gracefully back off on edit-conflict or if
    the page vanished (was deleted) before we got to save."""
    if not page.exists:
        print(f"   • skipped save, page [[{page.name}]] no longer exists")
        return False

    # Nothing to do if text hasn't changed
    try:
        current = page.text()
    except Exception:
        current = None
    if current is not None and current.rstrip() == text.rstrip():
        return False

    try:
        page.save(text, summary=summary)
        return True
    except mwclient.errors.EditError as e:
        if getattr(e, "code", "") == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
    except mwclient.errors.APIError as e:
        if e.code == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
    except Exception as e:
        print(f"   ! Save failed on [[{page.name}]] – {e}")
        return False


def get_interwikis(text):
    """Extract all interwiki links from text.
    Returns list of tuples: (language_code, category_title)
    """
    matches = INTERWIKI_RE.findall(text)
    result = []
    for lang, title in matches:
        # Strip "Category:" prefix if present (interwiki links often include namespace)
        if title.lower().startswith('category:'):
            title = title[9:]  # Remove "Category:" prefix
        result.append((lang.lower(), title))
    return result


def query_wikipedia_for_wikidata(lang_code, category_title):
    """Query a specific Wikipedia language edition for a category article
    and return its Wikidata ID if found.

    Returns a list of QIDs (could be multiple if there are multiple items)
    """
    try:
        # Normalize title - replace spaces with underscores for API
        normalized_title = category_title.replace(' ', '_')

        # Query the language Wikipedia API
        url = f"https://{lang_code}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": f"Category:{normalized_title}",
            "prop": "pageprops",
            "format": "json"
        }
        headers = {
            "User-Agent": "WikidataBot/1.0 (https://shinto.miraheze.org/; bot for adding wikidata links)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Navigate to pages
        if "query" not in data or "pages" not in data["query"]:
            return []

        pages = data["query"]["pages"]

        # Check each page for wikidata id
        qids = []
        for page_id, page_data in pages.items():
            # Check if page exists (page_id will be negative if missing)
            if int(page_id) < 0:
                continue

            # Check for pageprops with wikidata id
            if "pageprops" in page_data and "wikibase_item" in page_data["pageprops"]:
                qid = page_data["pageprops"]["wikibase_item"]
                if qid:
                    qids.append(qid.upper())

        return list(set(qids))  # Remove duplicates
    except Exception as e:
        return []


def has_wikidata_link(text):
    """Check if page already has {{wikidata link|Q...}} template."""
    return bool(WIKIDATA_TEMPLATE_RE.search(text))


def extract_existing_qids(text):
    """Extract all existing Wikidata QIDs from the page."""
    matches = WIKIDATA_TEMPLATE_RE.findall(text)
    return [match[0].upper() for match in matches]


def add_wikidata_links_and_category(text, qids, found_any_wikidata):
    """Add wikidata link templates and/or missing wikidata category."""
    # Remove any existing wikidata templates to re-add them fresh
    text_without_wikidata = WIKIDATA_TEMPLATE_RE.sub('', text)

    # Extract existing categories
    categories = CATEGORY_RE.findall(text_without_wikidata)
    text_without_cats = CATEGORY_RE.sub('', text_without_wikidata)

    # Build new content
    content = text_without_cats.rstrip()

    # Add wikidata link templates if found
    if qids:
        for qid in sorted(set(qids)):  # Remove duplicates and sort
            content += f"\n{{{{wikidata link|{qid}}}}}"

    # Add missing wikidata category if no wikidata was found
    if not found_any_wikidata:
        content += "\n[[Category:categories missing wikidata]]"

    # Ensure category list
    if categories:
        content += "\n\n"
        # Add categories back
        categories = list(dict.fromkeys(categories))  # Deduplicate
        content += "\n".join(f"[[Category:{cat}]]" for cat in categories)

    content += "\n"

    return content


def process_category_page(page):
    """Process a single category page to add Wikidata links from interwikis."""
    try:
        original_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Skip if already has wikidata links
    if has_wikidata_link(original_text):
        existing_qids = extract_existing_qids(original_text)
        print(f"   • [[{page.name}]] already has wikidata: {', '.join(existing_qids)}")
        return False

    # Get all interwiki links
    interwikis = get_interwikis(original_text)
    if not interwikis:
        print(f"   • [[{page.name}]] has no interwiki links")
        # Add missing wikidata category since we can't resolve any
        new_text = add_wikidata_links_and_category(original_text, [], False)
        if new_text != original_text:
            if safe_save(page, new_text, "Bot: add [[Category:categories missing wikidata]] (no interwikis found)"):
                print(f"   • tagged [[{page.name}]] as missing wikidata")
                return True
        return False

    # Query each interwiki for wikidata
    all_qids = []
    queries_made = 0
    for lang_code, category_title in interwikis:
        qids = query_wikipedia_for_wikidata(lang_code, category_title)
        if qids:
            all_qids.extend(qids)
            queries_made += 1
        time.sleep(0.3)  # Rate limit Wikipedia API calls

    # Deduplicate QIDs
    all_qids = list(set(all_qids))

    # Add wikidata links and/or missing wikidata category
    found_any = len(all_qids) > 0
    new_text = add_wikidata_links_and_category(original_text, all_qids, found_any)

    # Save if changed
    if new_text != original_text:
        if found_any:
            summary = f"Bot: add wikidata links from interwikis ({', '.join(all_qids)})"
            if safe_save(page, new_text, summary):
                print(f"   • added wikidata to [[{page.name}]]: {', '.join(all_qids)}")
                return True
        else:
            summary = "Bot: tag as missing wikidata (no wikidata found via interwikis)"
            if safe_save(page, new_text, summary):
                print(f"   • tagged [[{page.name}]] as missing wikidata")
                return True

    return False


def main():
    """Process all category pages."""

    print(f"Starting category namespace processing at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get all pages in Category namespace (namespace 14)
    print("Fetching all pages in Category namespace...")
    try:
        category_pages = site.allpages(namespace=14, limit=None)
    except Exception as e:
        print(f"ERROR: Could not fetch category pages – {e}")
        return

    # Convert to list to get count
    all_categories = list(category_pages)
    print(f"Found {len(all_categories)} category pages to process\n")

    modified_count = 0
    for idx, page in enumerate(all_categories, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            if process_category_page(page):
                modified_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Modified {modified_count} category pages.")


if __name__ == "__main__":
    main()
