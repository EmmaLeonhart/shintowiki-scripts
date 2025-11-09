"""undo_template_wikidata_category_edits.py
================================================
Undo all edits from the past 2 hours on pages in [[Category:Templates missing wikidata]].
================================================

This script:
1. Gets all pages in [[Category:Templates missing wikidata]]
2. For each page, removes {{wikidata link|Q...}} and [[Category:templates missing wikidata]]
   that were added by our bot scripts in the past 2 hours
3. Saves the modified pages
"""

import os
import time
import datetime
import mwclient
import re
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

# Time window to revert (in seconds)
REVERT_WINDOW = 2 * 60 * 60  # 2 hours

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")


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


def get_page_revisions_via_api(page_title, limit=50):
    """Get revision history for a page using mwclient's authenticated API."""
    try:
        result = site.api('query', titles=page_title, prop='revisions', rvprop='timestamp|user|comment', rvlimit=limit, format='json')

        if "query" not in result or "pages" not in result["query"]:
            return []

        pages = result["query"]["pages"]
        for page_id, page_data in pages.items():
            if "revisions" in page_data:
                return page_data["revisions"]

        return []
    except Exception as e:
        return []


def process_page(page):
    """Check if page has bot-added content and remove it."""
    try:
        current_text = page.text()
    except Exception as e:
        print(f"   ! could not read [[{page.name}]] – {e}")
        return False

    # Get revision history to check if this page was edited by us recently
    revisions = get_page_revisions_via_api(page.name, limit=20)
    if not revisions:
        return False

    # Get current time in UTC
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_time = now - datetime.timedelta(seconds=REVERT_WINDOW)

    # Check if any recent edits match our bot patterns
    has_recent_bot_edit = False
    bot_comments = [
        "Bot: add wikidata links from interwikis",
        "Bot: tag as missing wikidata",
    ]

    for revision in revisions[:10]:  # Check only recent revisions
        try:
            rev_timestamp = revision.get('timestamp')
            rev_comment = revision.get('comment', '')

            if not rev_timestamp:
                continue

            # Parse timestamp
            rev_time = datetime.datetime.strptime(rev_timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)

            # If within 2-hour window and is a bot comment, flag it
            if rev_time > cutoff_time and any(pattern in rev_comment for pattern in bot_comments):
                has_recent_bot_edit = True
                break
        except Exception:
            continue

    if not has_recent_bot_edit:
        return False

    # Remove what we added: {{wikidata link|Q...}} and [[Category:templates missing wikidata]]
    new_text = current_text

    # Remove {{wikidata link|Q...}} templates
    new_text = re.sub(r'\{\{wikidata link\|[Qq]\d+\}\}\n?', '', new_text)

    # Remove [[Category:templates missing wikidata]]
    new_text = re.sub(r'\[\[Category:templates missing wikidata\]\]\n?', '', new_text)

    # Clean up any excessive blank lines
    new_text = re.sub(r'\n\n\n+', '\n\n', new_text)

    if new_text != current_text:
        if safe_save(page, new_text, "Bot: undo wikidata additions from past 2 hours"):
            print(f"   ✓ reverted [[{page.name}]]")
            return True

    return False


def main():
    """Process all pages in the category and undo recent edits."""

    print(f"Starting undo process at {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print(f"Will undo edits from the past {REVERT_WINDOW // 3600} hour(s)\n")

    print("Fetching pages from [[Category:Templates missing wikidata]]...\n")

    try:
        # Get the category page
        category = site.pages['Category:Templates missing wikidata']
        pages = list(category)
    except Exception as e:
        print(f"ERROR: Could not fetch category – {e}")
        return

    if not pages:
        print("No pages found in [[Category:Templates missing wikidata]]")
        return

    print(f"Found {len(pages)} pages to check\n")

    reverted_count = 0
    for idx, page in enumerate(pages, 1):
        try:
            print(f"{idx}. [[{page.name}]]")
            if process_page(page):
                reverted_count += 1
        except Exception as e:
            try:
                print(f"{idx}. [[{page.name}]] – ERROR: {e}")
            except UnicodeEncodeError:
                print(f"{idx}. [page] – ERROR: {str(e)}")

        # Rate limiting to be kind to the server
        time.sleep(0.5)

    print(f"\nDone! Reverted {reverted_count} pages.")


if __name__ == "__main__":
    main()
