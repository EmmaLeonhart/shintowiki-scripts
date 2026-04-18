#!/usr/bin/env python3
"""
populate_namespace_layers.py
=============================
Copies mainspace page content into the Data: and Export: namespace layers.

For each mainspace page that has a {{wikidata link|QID}}:

  Data:<PageName>   — JSON blob with the QID and basic metadata
  Export:<PageName>  — full wikitext copy of the mainspace page

This script does NOT run automatically in the cleanup loop yet.
It is gated behind --enable-namespace-layers and will be activated
once the Data: and Export: namespaces are created on the wiki.

* Stateful — tracks processed pages in a .state file.
* Processes up to --max-edits pages per run (default 50).
* When all pages have been processed, the state file resets.

Default mode is dry-run. Use --apply to actually edit.
"""

import argparse
import io
import json
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

STATE_FILE = os.path.join(os.path.dirname(__file__), "populate_namespace_layers.state")

USER_AGENT = "NamespaceLayerBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Matches {{wikidata link|QID}} and captures the QID
WD_LINK_RE = re.compile(r'\{\{wikidata link\|\s*(Q\d+)\s*(?:\|[^}]*)?\}\}', re.IGNORECASE)

REDIRECT_RE = re.compile(r'^\s*#redirect\b', re.IGNORECASE | re.MULTILINE)

# Interwiki-prefixed pages sitting in mainspace
INTERWIKI_RE = re.compile(r'^[A-Za-z]{2,}:')

LOCAL_NS_PREFIXES = (
    "Category:", "Template:", "Module:", "Help:", "Talk:", "User:",
    "File:", "MediaWiki:", "Shinto Wiki:", "Wikipedia:",
    "User talk:", "Template talk:", "Category talk:", "File talk:",
    "Help talk:", "Module talk:", "MediaWiki talk:",
)


# ─── STATE ──────────────────────────────────────────────────

def load_state(path):
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                done.add(s)
    return done


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state(path):
    with open(path, "w", encoding="utf-8") as f:
        pass


# ─── HELPERS ────────────────────────────────────────────────

def iter_all_pages(site, namespace):
    """Yield all page titles in a given namespace via the allpages API."""
    params = {
        "list": "allpages",
        "apnamespace": namespace,
        "aplimit": "max",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def build_data_json(title, qid, text):
    """Build the JSON content for a Data: page."""
    data = {
        "qid": qid,
        "title": title,
        "schema_version": 1,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_export_wikitext(title, text):
    """Build the wikitext content for an Export: page.

    For now this is a straight copy of mainspace content.
    In future this will be the ILL/QID-enriched version while
    mainspace gets simplified to plain [[links]].
    """
    return text


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Populate Data: and Export: namespace layers from mainspace."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Max mainspace pages to process per run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    parser.add_argument("--enable-namespace-layers", action="store_true",
                        help="Required flag to actually run. Without this, the script exits immediately.")
    args = parser.parse_args()

    if not args.enable_namespace_layers:
        print("Namespace layers not enabled. Pass --enable-namespace-layers to run.")
        print("(Waiting for Data: and Export: namespaces to be created on the wiki.)")
        return

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    done = load_state(STATE_FILE) if args.apply else set()
    print(f"State: {len(done)} pages already processed")

    data_written = export_written = skipped = no_qid = errors = 0
    checked = 0
    finished_all = True

    print(f"\n--- Scanning mainspace (ns 0) ---")

    for title in iter_all_pages(site, 0):
        if args.max_edits and checked >= args.max_edits:
            print(f"Reached max checks ({args.max_edits}); stopping.")
            finished_all = False
            break

        if title in done:
            continue

        # Skip interwiki-prefixed pages
        if INTERWIKI_RE.match(title) and not title.startswith(LOCAL_NS_PREFIXES):
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        checked += 1

        if checked % 500 == 0:
            print(f"  ... processed {checked} pages ({data_written} Data:, {export_written} Export:)")

        try:
            page = site.pages[title]
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"[{checked}] {title} ERROR reading: {e}")
            errors += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        if not page.exists:
            skipped += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        if REDIRECT_RE.search(text):
            skipped += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        # Extract QID from {{wikidata link|...}}
        m = WD_LINK_RE.search(text)
        if not m:
            no_qid += 1
            if args.apply:
                append_state(STATE_FILE, title)
            continue

        qid = m.group(1)

        # Build namespace layer content
        data_content = build_data_json(title, qid, text)
        export_content = build_export_wikitext(title, text)

        data_title = f"Data:{title}"
        export_title = f"Export:{title}"

        if not args.apply:
            print(f"[{checked}] {title} ({qid}) DRY RUN: would create {data_title} + {export_title}")
            continue

        # Write Data: page
        try:
            data_page = site.pages[data_title]
            data_page.save(
                data_content,
                summary=f"Bot: populate Data: layer from mainspace ({qid}) {args.run_tag}",
            )
            data_written += 1
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {data_title} ERROR saving: {e}")
            errors += 1

        # Write Export: page
        try:
            export_page = site.pages[export_title]
            export_page.save(
                export_content,
                summary=f"Bot: populate Export: layer from mainspace {args.run_tag}",
            )
            export_written += 1
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {export_title} ERROR saving: {e}")
            errors += 1

        print(f"[{checked}] {title} ({qid}) → Data: + Export:")
        append_state(STATE_FILE, title)

    if finished_all and args.apply:
        print("\nAll pages fully processed — clearing state for next cycle.")
        clear_state(STATE_FILE)

    print(f"\n{'='*60}")
    print(f"Checked:       {checked}")
    print(f"Data: written: {data_written}")
    print(f"Export: written:{export_written}")
    print(f"No QID:        {no_qid}")
    print(f"Skipped:       {skipped}")
    print(f"Errors:        {errors}")


if __name__ == "__main__":
    main()
