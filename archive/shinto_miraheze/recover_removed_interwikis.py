#!/usr/bin/env python3
"""
Recover interwiki links that were removed by the cleanup script.

Queries the edit history of pages in [[Category:Pages with contradicting interwikis]]
to find what interwikis were removed in the v24 cleanup edits.
"""

import re
import sys
import time
import mwclient
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to wiki
site = mwclient.Site('shinto.miraheze.org', force_login=False)

INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')

def extract_interwikis(text):
    """Extract all interwiki links from text."""
    matches = INTERWIKI_RE.findall(text)
    return [(lang.lower(), title) for lang, title in matches]

def get_page_revisions(page_title, limit=10):
    """Get recent revisions of a page."""
    try:
        page = site.pages[page_title]
        revisions = list(page.revisions(limit=limit))
        return revisions
    except Exception as e:
        print(f"Error getting revisions for {page_title}: {e}")
        return []

def get_revision_text(revision):
    """Get the text content of a specific revision."""
    try:
        # Access the text property of the revision
        if 'slots' in revision:
            # MediaWiki 1.32+ format
            return revision['slots']['main']['*']
        else:
            # Older format
            return revision.get('*', '')
    except Exception as e:
        print(f"Error getting revision text: {e}")
        return None

def main():
    print("Recovering removed interwiki links from v24 cleanup")
    print("=" * 70)

    # Get pages in conflict category
    category = site.pages['Category:Pages with contradicting interwikis']
    pages = list(category.members())

    print(f"Found {len(pages)} pages with conflicting interwikis\n")

    removed_interwikis = []

    for i, page in enumerate(pages, 1):
        page_title = page.name

        print(f"{i:3d}. {page_title:50s}", end=' ', flush=True)

        # Get revisions (look for v24 cleanup edits)
        revisions = get_page_revisions(page_title, limit=20)

        if not revisions or len(revisions) < 2:
            print("[ERROR: Not enough revisions]")
            continue

        # Find the v24 cleanup edit
        v24_revision = None
        before_revision = None

        for j, rev in enumerate(revisions):
            comment = rev.get('comment', '')
            if 'v24 interwiki cleanup' in comment:
                v24_revision = rev
                # The revision before this one is what we need to compare
                if j + 1 < len(revisions):
                    before_revision = revisions[j + 1]
                break

        if not v24_revision or not before_revision:
            print("[NO v24 CLEANUP FOUND]")
            continue

        # Get text before and after cleanup
        # For older revisions, we need to fetch the full page content
        try:
            # Get the before version
            before_page = site.pages[page_title]
            before_text = None

            # We'll need to reconstruct by fetching old versions
            # For now, let's try a different approach: fetch the page diff

            # Actually, let's use the API to get the diff directly
            import requests

            before_revid = before_revision['revid']
            after_revid = v24_revision['revid']

            # Get both versions
            api_before = site.api(
                'query',
                prop='revisions',
                revids=before_revid,
                rvprop='content'
            )

            api_after = site.api(
                'query',
                prop='revisions',
                revids=after_revid,
                rvprop='content'
            )

            # Extract text from responses
            before_text = None
            after_text = None

            for page_id, page_data in api_before.get('query', {}).get('pages', {}).items():
                revisions_data = page_data.get('revisions', [])
                if revisions_data:
                    before_text = revisions_data[0].get('*', '')

            for page_id, page_data in api_after.get('query', {}).get('pages', {}).items():
                revisions_data = page_data.get('revisions', [])
                if revisions_data:
                    after_text = revisions_data[0].get('*', '')

            if not before_text or not after_text:
                print("[ERROR: Could not fetch revision texts]")
                continue

            # Extract interwikis from both versions
            before_interwikis = extract_interwikis(before_text)
            after_interwikis = extract_interwikis(after_text)

            # Find removed interwikis
            removed = []
            for lang, title in before_interwikis:
                # Check if this (lang, title) pair still exists in after
                if (lang, title) not in after_interwikis:
                    removed.append((lang, title))

            if removed:
                print(f"[REMOVED {len(removed)}]")
                for lang, title in removed:
                    print(f"       - [[{lang}:{title}]]")
                    removed_interwikis.append({
                        'page': page_title,
                        'lang': lang,
                        'title': title
                    })
            else:
                print("[OK]")

        except Exception as e:
            print(f"[ERROR: {str(e)[:40]}]")

        time.sleep(0.3)

    # Write summary to file
    print("\n" + "=" * 70)
    print(f"Total removed interwiki links: {len(removed_interwikis)}")
    print("=" * 70)

    # Save to file for review
    if removed_interwikis:
        with open('removed_interwikis_log.txt', 'w', encoding='utf-8') as f:
            f.write("Removed Interwiki Links from v24 Cleanup\n")
            f.write("=" * 70 + "\n\n")

            current_page = None
            for item in removed_interwikis:
                if item['page'] != current_page:
                    if current_page is not None:
                        f.write("\n")
                    current_page = item['page']
                    f.write(f"{current_page}:\n")

                f.write(f"  - [[{item['lang']}:{item['title']}]]\n")

        print(f"Removed interwikis logged to: removed_interwikis_log.txt")

if __name__ == '__main__':
    main()
