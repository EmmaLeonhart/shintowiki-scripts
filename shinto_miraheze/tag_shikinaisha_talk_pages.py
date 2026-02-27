"""
tag_shikinaisha_talk_pages.py
==============================
For every page in Category:Wikidata_generated_shikinaisha_pages, adds the
following section to its talk page if not already present:

    ==This page was generated from Wikidata==
    This page was originally generated programmatically from [[d:QID]] ~~~~

Default mode is dry-run. Use --apply to save edits.

Examples:
    python shinto_miraheze/tag_shikinaisha_talk_pages.py --limit 10
    python shinto_miraheze/tag_shikinaisha_talk_pages.py --apply
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
THROTTLE = 1.5
CATEGORY = "Wikidata_generated_shikinaisha_pages"
DEFAULT_STATE_FILE = "shinto_miraheze/tag_shikinaisha_talk_pages.state"

QID_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)\s*[\|\}]", re.IGNORECASE)
SECTION_RE = re.compile(r"==\s*This page was generated from Wikidata\s*==", re.IGNORECASE)


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


def extract_qid(page_text):
    m = QID_RE.search(page_text or "")
    return m.group(1).upper() if m else None


def build_section(qid):
    link = f"[[d:{qid}]]" if qid else "''(QID not found)''"
    return (
        "\n==This page was generated from Wikidata==\n"
        f"This page was originally generated programmatically from {link} ~~~~\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process (0 = no limit).")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="Path to resume-state file.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="ShikinaishaTalkTaggerBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    completed = load_state(args.state_file) if args.apply else set()
    if args.apply:
        print(f"Loaded {len(completed)} completed titles from state file: {args.state_file}")

    cat = site.categories[CATEGORY]
    processed = edited = skipped = errors = 0

    for page in cat:
        if page.namespace != 0:
            continue
        title = page.name
        if args.limit and processed >= args.limit:
            break
        if args.apply and title in completed:
            skipped += 1
            continue

        processed += 1
        prefix = f"[{processed}] {title}"
        talk_title = f"Talk:{title}"

        try:
            page_text = page.text() if page.exists else ""
            talk_page = site.pages[talk_title]
            talk_text = talk_page.text() if talk_page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading: {e}")
            errors += 1
            continue

        if SECTION_RE.search(talk_text):
            print(f"{prefix} SKIP (section already present)")
            skipped += 1
            if args.apply:
                append_state(args.state_file, title)
                completed.add(title)
            continue

        qid = extract_qid(page_text)
        if not qid:
            print(f"{prefix} WARN no QID found in page text")

        new_talk_text = (talk_text.rstrip() + build_section(qid)).strip() + "\n"

        if not args.apply:
            print(f"{prefix} DRY RUN would add section (qid={qid})")
            continue

        try:
            talk_page.save(
                new_talk_text,
                summary=f"Bot: add Wikidata generation notice ([[d:{qid}]])" if qid else "Bot: add Wikidata generation notice",
            )
            edited += 1
            print(f"{prefix} EDITED (qid={qid})")
            append_state(args.state_file, title)
            completed.add(title)
            time.sleep(THROTTLE)
        except Exception as e:
            msg = str(e).lower()
            if "nochange" in msg:
                print(f"{prefix} NOCHANGE")
                append_state(args.state_file, title)
                completed.add(title)
            else:
                print(f"{prefix} ERROR saving: {e}")
                errors += 1

    print(f"\n{'=' * 60}")
    print(
        f"Done. Processed: {processed} | Edited: {edited} | "
        f"Skipped: {skipped} | Errors: {errors} | Mode: {'APPLY' if args.apply else 'DRY-RUN'}"
    )


if __name__ == "__main__":
    main()
