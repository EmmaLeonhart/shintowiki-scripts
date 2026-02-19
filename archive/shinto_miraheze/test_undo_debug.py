"""test_undo_debug.py
Debug script to test revision fetching and timestamp parsing
Uses mwclient's authenticated session + direct API calls.
"""

import mwclient
import datetime
import sys

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

# Test with a sample template that was edited recently
test_page = "Template:125 Shrines of Ise"

print(f"Testing revision fetch for: {test_page}\n")

try:
    page = site.pages[test_page]
    print(f"Page exists: {page.exists}")
    print(f"Page name: {page.name}\n")

    # Use site.api to query revisions directly with mwclient's authenticated session
    print("Fetching revisions using mwclient's authenticated API session...\n")

    result = site.api('query', titles=test_page, prop='revisions', rvprop='timestamp|user|comment', rvlimit=10, format='json')

    pages = result['query']['pages']
    revisions = []
    for page_id, page_data in pages.items():
        if 'revisions' in page_data:
            revisions = page_data['revisions']
            break

    print(f"Found {len(revisions)} revisions:\n")

    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_time = now - datetime.timedelta(hours=2)

    print(f"Current time (UTC): {now}")
    print(f"Cutoff time (2 hours ago): {cutoff_time}\n")

    for idx, rev in enumerate(revisions):
        print(f"Revision {idx + 1}:")
        print(f"  Raw revision object keys: {rev.keys()}")
        print(f"  Timestamp raw: {rev.get('timestamp')}")
        print(f"  User: {rev.get('user', 'N/A')}")
        print(f"  Comment: {rev.get('comment', 'N/A')}")

        rev_timestamp = rev.get('timestamp')
        if rev_timestamp:
            try:
                # Handle both string and datetime.datetime objects
                if isinstance(rev_timestamp, str):
                    rev_time = datetime.datetime.strptime(rev_timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
                else:
                    rev_time = rev_timestamp
                    if rev_time.tzinfo is None:
                        rev_time = rev_time.replace(tzinfo=datetime.timezone.utc)

                print(f"  Parsed time: {rev_time}")
                print(f"  Within 2-hour window? {rev_time > cutoff_time}")
            except Exception as e:
                print(f"  Parse error: {e}")
        print()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
