"""find_unclosed_brackets.py
================================================
Find pages with unclosed parentheses, brackets, and braces
================================================

This script:
1. Walks through [[Category:Pages linked to Wikidata]]
2. Checks each page for unclosed (), {}, and []
3. Adds appropriate categories:
   - [[Category:Pages with unclosed parentheses]]
   - [[Category:Pages with unclosed curly braces]]
   - [[Category:Pages with unclosed square brackets]]
"""

import mwclient
import sys
import time
import re

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def count_brackets(text, open_char, close_char):
    """Count opening and closing bracket pairs, accounting for nested structures."""
    open_count = 0
    close_count = 0

    # Iterate through each character
    for i, char in enumerate(text):
        if char == open_char:
            # Check if it's escaped (preceded by backslash)
            if i == 0 or text[i-1] != '\\':
                open_count += 1
        elif char == close_char:
            if i == 0 or text[i-1] != '\\':
                close_count += 1

    return open_count, close_count


def has_unclosed_brackets(text):
    """Check if text has unclosed parentheses, brackets, or braces."""
    results = {
        'parentheses': False,
        'square': False,
        'curly': False,
    }

    # Check parentheses ()
    open_p, close_p = count_brackets(text, '(', ')')
    if open_p != close_p:
        results['parentheses'] = True

    # Check square brackets []
    open_s, close_s = count_brackets(text, '[', ']')
    if open_s != close_s:
        results['square'] = True

    # Check curly braces {}
    open_c, close_c = count_brackets(text, '{', '}')
    if open_c != close_c:
        results['curly'] = True

    return results


def has_category(page_text, category_name):
    """Check if a page already has a category."""
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]'
    return bool(re.search(pattern, page_text, re.IGNORECASE))


def add_category(page_text, category_name):
    """Add a category to the page if it doesn't already have it."""
    if has_category(page_text, category_name):
        return page_text

    # Add category at the end
    return page_text.rstrip() + f"\n[[Category:{category_name}]]"


def remove_category(page_text, category_name):
    """Remove a category from the page."""
    pattern = r'\[\[Category:' + re.escape(category_name) + r'\]\]\n?'
    return re.sub(pattern, '', page_text, flags=re.IGNORECASE)


def main():
    """Process all pages in [[Category:Pages linked to Wikidata]]."""

    print("Finding pages with unclosed brackets\n")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Pages linked to Wikidata']

    print(f"\nFetching mainspace pages in [[Category:Pages linked to Wikidata]]...")
    try:
        all_members = list(category.members())
        # Filter to mainspace only (namespace 0)
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")

    processed_count = 0
    paren_count = 0
    square_count = 0
    curly_count = 0
    error_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end="")

            # Get page text
            text = page.text()

            # Check for unclosed brackets
            unclosed = has_unclosed_brackets(text)

            # Track what was found
            found_issues = []

            if unclosed['parentheses']:
                found_issues.append("()")
                text = add_category(text, "Pages with unclosed parentheses")
                paren_count += 1
            else:
                text = remove_category(text, "Pages with unclosed parentheses")

            if unclosed['square']:
                found_issues.append("[]")
                text = add_category(text, "Pages with unclosed square brackets")
                square_count += 1
            else:
                text = remove_category(text, "Pages with unclosed square brackets")

            if unclosed['curly']:
                found_issues.append("{}")
                text = add_category(text, "Pages with unclosed curly braces")
                curly_count += 1
            else:
                text = remove_category(text, "Pages with unclosed curly braces")

            # Only save if there were changes
            if found_issues or has_category(page_text := page.text(), "Pages with unclosed parentheses") or has_category(page_text, "Pages with unclosed square brackets") or has_category(page_text, "Pages with unclosed curly braces"):
                try:
                    page.edit(text, summary="Bot: categorize pages with unclosed brackets")
                    processed_count += 1
                    if found_issues:
                        print(f" ... ✓ Unclosed: {', '.join(found_issues)}")
                    else:
                        print(f" ... • Cleaned up (no issues)")
                except mwclient.errors.EditConflict:
                    print(f" ! Edit conflict")
                    error_count += 1
                except Exception as e:
                    print(f" ! Error saving: {e}")
                    error_count += 1
            else:
                print(f" ... • OK")

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")
            error_count += 1

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  Pages with unclosed parentheses: {paren_count}")
    print(f"  Pages with unclosed square brackets: {square_count}")
    print(f"  Pages with unclosed curly braces: {curly_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main()
