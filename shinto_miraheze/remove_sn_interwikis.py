"""
remove_sn_interwikis.py
========================
Removes all [[sn:...]] interwiki links from every page on shintowiki.

These were accidentally added as fake interwiki links during earlier bot
passes — e.g. [[sn:This category was created from JA→Wikidata links on X]].
The "sn" language code was used to store descriptive notes, which is
meaningless and should be stripped entirely.

Finds affected pages via the MediaWiki langlinks API (lllang=sn), then
strips all [[sn:...]] occurrences from each page's wikitext.

Run dry-run first:
    python remove_sn_interwikis.py --dry-run
"""

import os
import re
import time
import io
import sys
import argparse
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
THROTTLE  = 1.5

SN_RE = re.compile(r'\[\[sn:[^\]]*\]\]\n?', re.IGNORECASE)


def get_pages_with_sn(site):
    """Return list of page titles that have [[sn:...]] links, via full-text search."""
    titles = []
    params = {
        "list": "search",
        "srsearch": "insource:\"[[sn:\"",
        "srnamespace": "*",
        "srlimit": 500,
        "srwhat": "text",
    }
    while True:
        result = site.api("query", **params)
        for entry in result["query"]["search"]:
            titles.append(entry["title"])
        if "continue" in result:
            params.update(result["continue"])
        else:
            break
    return titles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="SnInterwikiRemoverBot/1.0 (User:EmmaBot; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    print("Finding pages with [[sn:...]] links...")
    titles = get_pages_with_sn(site)
    # Deduplicate — a page can appear multiple times if it has multiple sn: links
    titles = list(dict.fromkeys(titles))
    print(f"Found {len(titles)} pages with [[sn:...]] links\n")

    cleaned = skipped = errors = 0

    for i, title in enumerate(titles, 1):
        page = site.pages[title]
        try:
            text = page.text()
        except Exception as e:
            print(f"[{i}/{len(titles)}] ERROR reading {title}: {e}")
            errors += 1
            continue

        new_text = SN_RE.sub("", text)

        if new_text == text:
            print(f"[{i}/{len(titles)}] SKIP (no sn: found in text): {title}")
            skipped += 1
            continue

        count = len(SN_RE.findall(text))
        if args.dry_run:
            print(f"[{i}/{len(titles)}] DRY RUN: would remove {count} [[sn:...]] link(s) from {title}")
        else:
            try:
                page.save(new_text, summary="Bot: remove [[sn:...]] interwiki links (meaningless notes stored as fake interwikis)")
                print(f"[{i}/{len(titles)}] CLEANED ({count} removed): {title}")
                time.sleep(THROTTLE)
                cleaned += 1
            except Exception as e:
                print(f"[{i}/{len(titles)}] ERROR saving {title}: {e}")
                errors += 1

    print(f"\n{'='*60}")
    print(f"Done. Cleaned: {cleaned} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
