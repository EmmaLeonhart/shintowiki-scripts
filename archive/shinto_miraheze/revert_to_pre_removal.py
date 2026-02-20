#!/usr/bin/env python3
"""
Revert pages to pre-removal state by finding the most recent edit
whose summary does NOT start with "Remove" and restoring that version.
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

def main():
    """Main execution."""
    print("="*70)
    print("REVERT PAGES TO PRE-REMOVAL STATE")
    print("="*70)
    print()

    try:
        # Login to wiki
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        # Get all pages in category
        category_name = "Wikidata generated shikinaisha pages"
        print(f"Retrieving pages from [[Category:{category_name}]]...")

        reverted = []
        failed = []
        skipped = []
        page_count = 0

        # Iterate through category members
        try:
            for page in site.api('query', list='categorymembers', cmtitle=f'Category:{category_name}', cmlimit='max')['query']['categorymembers']:
                page_title = page['title']
                page_ns = page['ns']

                # Only process mainspace pages (ns=0)
                if page_ns != 0:
                    continue

                page_count += 1
                print(f"Processing {page_count}: {page_title}...", end=" ")

                try:
                    page_obj = site.pages[page_title]

                    # Get revision history
                    revisions = list(site.api('query', titles=page_title, prop='revisions',
                                             rvlimit='max', rvprop='timestamp|user|comment')['query']['pages'].values())[0].get('revisions', [])

                    if not revisions:
                        print("[NO REVISIONS]")
                        skipped.append(page_title)
                        continue

                    # Find the most recent revision whose comment does NOT start with "Remove"
                    target_revision = None
                    for rev in revisions:
                        comment = rev.get('comment', '')
                        if not comment.startswith('Remove'):
                            target_revision = rev
                            break

                    if not target_revision:
                        print("[NO PRE-REMOVAL REVISION]")
                        skipped.append(page_title)
                        continue

                    # Get the content of that revision
                    rev_id = target_revision.get('revid')
                    rev_content = site.api('query', titles=page_title, prop='revisions',
                                          revids=rev_id, rvprop='content')['query']['pages']

                    target_text = list(rev_content.values())[0]['revisions'][0]['*']

                    # Check if current text is different
                    current_text = page_obj.text()

                    if current_text == target_text:
                        print("[ALREADY REVERTED]")
                        skipped.append(page_title)
                    else:
                        # Revert to target version
                        page_obj.edit(target_text, summary="Revert to pre-removal state")
                        print("[REVERTED]")
                        reverted.append(page_title)

                    # Rate limit
                    time.sleep(1.5)

                except Exception as e:
                    print(f"[ERROR - {e}]")
                    failed.append((page_title, str(e)))
                    continue

        except Exception as e:
            print(f"Error retrieving category members: {e}")
            import traceback
            traceback.print_exc()

        # Summary
        print(f"\n{'='*70}")
        print(f"REVERSION SUMMARY")
        print(f"{'='*70}")
        print(f"Reverted: {len(reverted)}")
        print(f"Skipped: {len(skipped)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {page_count}")
        print()

        if reverted:
            print("REVERTED PAGES:")
            for page in reverted[:20]:  # Show first 20
                print(f"  {page}")
            if len(reverted) > 20:
                print(f"  ... and {len(reverted) - 20} more")
            print()

        if failed:
            print("FAILED PAGES:")
            for page, reason in failed[:10]:  # Show first 10
                print(f"  {page}: {reason}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
