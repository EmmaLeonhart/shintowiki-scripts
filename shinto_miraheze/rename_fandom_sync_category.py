#!/usr/bin/env python3
"""
rename_fandom_sync_category.py
===============================
One-shot legacy migration: rewrites every miraheze page that uses
[[Category:Fandom sync]] to use [[Category:Independently git synced
pages]] instead. The old name was misleading — it implied a wiki-to-wiki
sync, which is not what the category actually marks (it marks pages
whose miraheze and fandom forms are intentionally divergent and need
*independent* per-wiki git tracking).

Idempotent: a no-op once every page has been migrated. Safe to keep
wired into the pipeline indefinitely.

Also strips [[Category:Git synced pages]] when present alongside the
old fandom-sync tag, because pages migrating into the new bucket
should NOT also be in the original miraheze-only bucket — the
"independent" bucket takes precedence per the new architecture.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

OLD_CATEGORY = "Fandom sync"
NEW_CATEGORY = "Independently git synced pages"
CATEGORY_NAMESPACES = "0|10|14|828"

USER_AGENT = "FandomSyncCategoryRename/1.0 (User:EmmaBot)"

OLD_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Fandom sync\s*\]\]',
    re.IGNORECASE,
)
NEW_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Independently git synced pages\s*\]\]',
    re.IGNORECASE,
)
GIT_SYNCED_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Git synced pages\s*\]\]\s*\n?',
    re.IGNORECASE,
)


def category_members(site, category, namespaces):
    out = []
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmnamespace": namespaces,
        "cmlimit": "max",
        "formatversion": "2",
    }
    while True:
        result = site.api("query", **params)
        for m in result.get("query", {}).get("categorymembers", []) or []:
            out.append(m["title"])
        if "continue" in result:
            params.update(result["continue"])
        else:
            break
    return out


def transform(text: str) -> tuple[str, list[str]]:
    """Replace old category tag with new, drop Git synced pages tag.
    Returns (new_text, list_of_changes_made)."""
    changes = []
    new_text = text
    if OLD_RE.search(new_text):
        if NEW_RE.search(new_text):
            new_text = OLD_RE.sub("", new_text)
            changes.append(f"removed duplicate [[Category:{OLD_CATEGORY}]] (new tag already present)")
        else:
            new_text = OLD_RE.sub(f"[[Category:{NEW_CATEGORY}]]", new_text)
            changes.append(f"renamed [[Category:{OLD_CATEGORY}]] -> [[Category:{NEW_CATEGORY}]]")
    if GIT_SYNCED_RE.search(new_text):
        new_text = GIT_SYNCED_RE.sub("", new_text)
        changes.append("dropped [[Category:Git synced pages]] (independent bucket takes precedence)")
    return new_text, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max wiki edits per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL} as {USERNAME}")

    titles = category_members(site, OLD_CATEGORY, CATEGORY_NAMESPACES)
    print(f"[[Category:{OLD_CATEGORY}]] members: {len(titles)}")

    if not titles:
        print("Nothing to migrate. Done.")
        return 0

    edits = 0
    errors = 0
    skipped = 0

    for title in titles:
        if edits >= args.max_edits:
            skipped += 1
            continue
        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            errors += 1
            print(f"ERROR reading {title}: {e}")
            continue

        new_text, changes = transform(text)
        if not changes or new_text == text:
            print(f"SKIP  {title}  (no change needed)")
            continue

        summary = "Bot: " + "; ".join(changes) + f" {args.run_tag}"
        if not args.apply:
            print(f"[DRY] EDIT  {title}  ({'; '.join(changes)})")
            edits += 1
            continue
        try:
            page.save(new_text, summary=summary)
            edits += 1
            print(f"EDIT  {title}  ({'; '.join(changes)})")
            time.sleep(THROTTLE)
        except Exception as e:
            errors += 1
            print(f"ERROR saving {title}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Edits performed: {edits}")
    print(f"Skipped:         {skipped}")
    print(f"Errors:          {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
