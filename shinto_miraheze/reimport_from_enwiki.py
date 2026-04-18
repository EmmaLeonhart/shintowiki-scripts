#!/usr/bin/env python3
"""
reimport_from_enwiki.py
========================
Downloads XML exports from enwiki (with templates, current revision only)
and reimports them into shintowiki with mangled timestamps so that the
import always overwrites the current revision.

This fixes erroneous transclusions by pulling the full dependency tree
(templates, modules) from enwiki in one shot.

**How it works:**
1. Read page titles from a text file (one per line).
2. For each page, download its XML via enwiki Special:Export with
   ``templates=1`` and ``curonly=1``.
3. Replace ``timestamp`` with ``timestam`` in the XML so MediaWiki
   treats the import as having no timestamp — the import time becomes
   the revision time, forcing an overwrite even if the local revision
   is newer.
4. Import the modified XML into shintowiki via ``action=import``.

Default mode is dry-run.  Use ``--apply`` to actually import.
Processes only 1 page per run by default (``--max-imports 1``).
"""

import argparse
import io
import json
import os
import re
import sys
import time

import mwclient
import requests as requests_lib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

ENWIKI_EXPORT_URL = "https://en.wikipedia.org/w/index.php"
USER_AGENT = "EmmaBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

STATE_FILE = os.path.join(os.path.dirname(__file__), "reimport_from_enwiki.state")
ERRORS_FILE = os.path.join(os.path.dirname(__file__), "reimport_from_enwiki.errors")
DEFAULT_PAGES_FILE = os.path.join(
    os.path.dirname(__file__), "erroneous_transclusion_pages.txt"
)

# Known namespace prefixes that already have their namespace in the title.
KNOWN_PREFIXES = (
    "Module:", "Template:", "Help:", "Category:", "Wikipedia:",
    "MediaWiki:", "User:", "Talk:", "File:", "Shinto Wiki:",
)


def load_state(path):
    completed = set()
    if not os.path.exists(path):
        return completed
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                completed.add(s)
    return completed


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def append_error(title, error_msg):
    """Log a failed page to the errors file so it can be reviewed later."""
    with open(ERRORS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{title}\t{error_msg}\n")


def parse_pages_file(path):
    titles = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                titles.append(s)
    return titles


def download_enwiki_export(page_title):
    """Download XML export from enwiki for a single page with templates."""
    params = {
        "title": "Special:Export",
        "action": "submit",
    }
    data = {
        "pages": page_title,
        "templates": "1",
        "curonly": "1",
        "wpDownload": "1",
    }
    resp = requests_lib.post(
        ENWIKI_EXPORT_URL,
        params=params,
        data=data,
        headers={"User-Agent": USER_AGENT},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.text


def export_has_pages(xml_text):
    """Check if the XML export actually contains any <page> elements."""
    return "<page>" in xml_text


def mangle_timestamps(xml_text):
    """Replace 'timestamp' with 'timestam' so MediaWiki ignores revision dates."""
    return xml_text.replace("timestamp", "timestam")


def import_xml(site, xml_text, summary="", interwiki_prefix="en"):
    """Import XML into the wiki via action=import."""
    # Get CSRF token
    token_result = site.api("query", meta="tokens", type="csrf")
    csrf_token = token_result["query"]["tokens"]["csrftoken"]

    import_data = {
        "action": "import",
        "interwikiprefix": interwiki_prefix,
        "token": csrf_token,
        "format": "json",
    }
    if summary:
        import_data["summary"] = summary

    xml_bytes = xml_text.encode("utf-8")
    files = {
        "xml": ("import.xml", xml_bytes, "application/xml"),
    }

    raw_response = site.raw_call("api", import_data, files=files)
    result = json.loads(raw_response)

    if "error" in result:
        raise RuntimeError(
            f"Import API error: {result['error'].get('info', result['error'])}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Reimport pages from enwiki to fix erroneous transclusions."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually import (default is dry-run).",
    )
    parser.add_argument(
        "--max-imports", type=int, default=10,
        help="Max successful imports per run (default 10).",
    )
    parser.add_argument(
        "--max-errors", type=int, default=10,
        help="Bail if this many errors with zero successes (default 10).",
    )
    parser.add_argument(
        "--pages-file", default=DEFAULT_PAGES_FILE,
        help="Path to the page list file.",
    )
    parser.add_argument(
        "--state-file", default=STATE_FILE,
        help="Path to the state file for tracking completed imports.",
    )
    parser.add_argument(
        "--run-tag", required=True,
        help="Wiki-formatted run tag link for import summaries.",
    )
    args = parser.parse_args()

    pages = parse_pages_file(args.pages_file)
    if not pages:
        print("No pages found in page list file.")
        return

    completed = load_state(args.state_file) if args.apply else set()
    pending = [p for p in pages if p not in completed]
    print(f"Total pages: {len(pages)}, completed: {len(completed)}, pending: {len(pending)}")

    if not pending:
        print("All pages already processed.")
        return

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent=USER_AGENT,
    )
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    imported = skipped = errors = 0
    checked = 0

    for title in pending:
        if args.max_imports and imported >= args.max_imports:
            print(f"Reached max imports ({args.max_imports}); stopping.")
            break

        if imported == 0 and errors >= args.max_errors:
            print(f"Reached {args.max_errors} errors with zero successes; bailing.")
            break

        checked += 1
        prefix = f"[{checked}] {title}"

        # Download from enwiki
        try:
            print(f"{prefix} Downloading from enwiki...")
            xml = download_enwiki_export(title)

            # If no pages found and title has no namespace prefix, retry with Template:
            if not export_has_pages(xml):
                has_ns = any(title.startswith(p) for p in KNOWN_PREFIXES)
                if not has_ns:
                    alt_title = f"Template:{title}"
                    print(f"{prefix} No pages found, retrying as {alt_title}...")
                    xml = download_enwiki_export(alt_title)

            if not export_has_pages(xml):
                print(f"{prefix} SKIP (no page content found on enwiki)")
                skipped += 1
                if args.apply:
                    append_state(args.state_file, title)
                continue

            # Count pages in the export
            page_count = xml.count("<page>")
            print(f"{prefix} Downloaded {page_count} page(s) (with templates)")

        except Exception as e:
            print(f"{prefix} ERROR downloading: {e}")
            errors += 1
            append_error(title, f"download: {e}")
            if args.apply:
                append_state(args.state_file, title)
            continue

        # Mangle timestamps
        xml = mangle_timestamps(xml)

        if not args.apply:
            print(f"{prefix} DRY RUN: would import {page_count} page(s)")
            continue

        # Import into shintowiki
        try:
            summary = f"Bot: reimport from enwiki to fix erroneous transclusions {args.run_tag}"
            result = import_xml(site, xml, summary=summary)
            import_pages = result.get("import", [])
            print(f"{prefix} IMPORTED {len(import_pages)} page(s)")
            for ip in import_pages[:5]:
                print(f"    - {ip.get('title', '?')} (revisions: {ip.get('revisions', 0)})")
            if len(import_pages) > 5:
                print(f"    ... and {len(import_pages) - 5} more")
            imported += 1
            append_state(args.state_file, title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR importing: {e}")
            errors += 1
            append_error(title, f"import: {e}")
            if args.apply:
                append_state(args.state_file, title)

    print("\n" + "=" * 60)
    print(f"Checked:  {checked}")
    print(f"Imported: {imported}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")


if __name__ == "__main__":
    main()
