"""resolve_template_wikidata_from_interwiki_v2.py
================================================
Resolve Wikidata for template pages using interwiki links.
================================================

This script:
1. Iterates through ALL pages in the Template namespace
2. For each template page:
   - Finds all interwiki links (e.g., [[en:Template:XX]], [[de:Template:YY]])
   - Queries the foreign Wikipedia for the template article
   - Checks if that Wikipedia article has a Wikidata connection
   - Appends <noinclude>{{wikidata link|Q#####}}</noinclude> for each Wikidata item found
   - If no Wikidata found via interwikis, appends <noinclude>[[Category:Templates without wikidata]]</noinclude>
3. Handles all language interwikis
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
INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')

# Match existing {{wikidata link|Q...}} templates
WIKIDATA_TEMPLATE_RE = re.compile(r'{{wikidata link\|([Qq](\\d+))}')


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
    Returns list of tuples: (language_code, template_title)
    """
    matches = INTERWIKI_RE.findall(text)
    result = []
    for lang, title in matches:
        # Strip "Template:" prefix if present (interwiki links often include namespace)
        if title.lower().startswith('template:'):
            title = title[9:]  # Remove "Template:" prefix
        result.append((lang.lower(), title))
    return result


def query_wikipedia_for_wikidata(lang_code, template_title):
    """Query a specific Wikipedia language edition for a template article
    and return its Wikidata ID if found.

    Returns a list of QIDs (could be multiple if there are multiple items)
    """
    try:
        # Normalize title - replace spaces with underscores for API
        normalized_title = template_title.replace(' ', '_')

        # Query the language Wikipedia API
        url = f"https://{lang_code}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": f"Template:{normalized_title}",
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


def append_noinclude_section(text, qids, found_any_wikidata):
    """Append a <noinclude> section at the end with wikidata link or missing category."""
    # Ensure text ends with newline
    if not text.endswith('\n'):
        text += '\n'

    # Build noinclude content
    noinclude = '<noinclude>'

    if qids:
        # Add wikidata link templates
        for qid in sorted(set(qids)):  # Remove duplicates and sort
            noinclude += f'{{{{wikidata link|{qid}}}}}'

    if not found_any_wikidata:
        # Add missing wikidata category
        noinclude += '[[Category:Templates without wikidata]]'

    noinclude += '</noinclude>\n'

    return text + noinclude


def process_template_page(page):
    """Process a single template page to add Wikidata links from interwikis."""
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
        # Append missing wikidata category since we can't resolve any
        new_text = append_noinclude_section(original_text, [], False)
        if safe_save(page, new_text, "Bot: add {{wikidata link|Q...}} or [[Category:Templates without wikidata]]"):
            print(f"   • tagged [[{page.name}]] as missing wikidata")
            return True
        return False

    # Query each interwiki for wikidata
    all_qids = []
    queries_made = 0
    for lang_code, template_title in interwikis:
        qids = query_wikipedia_for_wikidata(lang_code, template_title)
        if qids:
            all_qids.extend(qids)
            queries_made += 1
        time.sleep(0.3)  # Rate limit Wikipedia API calls

    # Deduplicate QIDs
    all_qids = list(set(all_qids))

    # Append noinclude section
    found_any = len(all_qids) > 0
    new_text = append_noinclude_section(original_text, all_qids, found_any)

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
    """Process all template pages."""

    print(f"Starting template namespace processing at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get all pages in Template namespace (namespace 10)
    print("Fetching all pages in Template namespace...")
    try:
        template_pages = site.allpages(namespace=10, limit=None)
    except Exception as e:
        print(f"ERROR: Could not fetch template pages – {e}")
        return

    # Convert to list to get count
    all_templates = list(template_pages)
    print(f"Found {len(all_templates)} template pages to process\n")

    modified_count = 0
    for idx, page in enumerate(all_templates, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            if process_template_page(page):
                modified_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Modified {modified_count} template pages.")


if __name__ == "__main__":
    main()
