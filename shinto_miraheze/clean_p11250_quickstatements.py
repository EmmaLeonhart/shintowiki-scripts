#!/usr/bin/env python3
"""
clean_p11250_quickstatements.py
================================
Reads [[QuickStatements/P11250]] on shintowiki and checks each QS line
against Wikidata. If the Wikidata item now has the correct P11250 value,
the line is removed from the page.

This is the cleanup counterpart to generate_p11250_quickstatements.py,
which adds lines. This script only removes lines that are no longer
needed.

Processes up to --max-checks items per run (default 100).
Default mode is dry-run. Use --apply to actually edit the wiki page.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 1.5

QS_PAGE_TITLE = "QuickStatements/P11250"

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')

QS_PAGE_HEADER = """\
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P11250 P11250] (Miraheze article ID) to Wikidata.

Each line below adds a <code>P11250</code> claim linking a Wikidata item to its corresponding page on [https://shinto.miraheze.org shinto.miraheze.org]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"

# Retry session — 429 is excluded (immediate termination)
_retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://", HTTPAdapter(max_retries=_retry_strategy))


# ─── HELPERS ────────────────────────────────────────────────

def get_wikidata_p11250(qid):
    """
    Fetch P11250 values for a Wikidata item.
    Returns a list of string values, or None on error.
    """
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        resp = _http.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if resp.status_code == 429:
            print(f"   ! FATAL: 429 Too Many Requests — terminating", file=sys.stderr)
            sys.exit(1)
        resp.raise_for_status()
        entity = resp.json().get("entities", {}).get(qid, {})
        claims = entity.get("claims", {}).get("P11250", [])
        values = []
        for claim in claims:
            dv = claim.get("mainsnak", {}).get("datavalue", {})
            if dv.get("type") == "string":
                values.append(dv["value"])
        return values
    except Exception as e:
        print(f"   ! error fetching P11250 for {qid}: {e}")
        return None


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove completed P11250 QuickStatements from the wiki page."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit the QS page (default is dry-run).")
    parser.add_argument("--max-checks", type=int, default=100,
                        help="Max QS lines to check per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # Read existing QS page
    qs_page = site.pages[QS_PAGE_TITLE]
    try:
        existing_text = qs_page.text() if qs_page.exists else ""
    except Exception as e:
        print(f"ERROR reading [[{QS_PAGE_TITLE}]]: {e}")
        return

    # Parse QS lines
    qs_entries = {}  # qid -> expected_value
    for line in existing_text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            qs_entries[m.group(1)] = f"shinto:{m.group(2)}"

    print(f"Found {len(qs_entries)} QS lines on [[{QS_PAGE_TITLE}]]")

    if not qs_entries:
        print("Nothing to check.")
        return

    # Check each QS line against Wikidata
    checked = 0
    removed = []
    errors = 0

    for qid, expected in list(qs_entries.items()):
        if args.max_checks and checked >= args.max_checks:
            print(f"Reached max checks ({args.max_checks}); stopping.")
            break

        checked += 1

        p11250_values = get_wikidata_p11250(qid)
        if p11250_values is None:
            errors += 1
            continue

        if expected in p11250_values:
            print(f"[{checked}] {qid} — P11250={expected} now on Wikidata, removing")
            removed.append(qid)
        else:
            # Still needed
            pass

        time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"Checked:  {checked}")
    print(f"Removed:  {len(removed)}")
    print(f"Errors:   {errors}")

    if not removed:
        print("No lines to remove.")
        return

    # Rebuild page without removed lines
    remaining = {qid: val for qid, val in qs_entries.items() if qid not in removed}
    qs_lines = []
    for qid in sorted(remaining.keys()):
        qs_lines.append(f'{qid}|P11250|"{remaining[qid]}"')

    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=f"Bot: remove {len(removed)} completed P11250 QuickStatements {args.run_tag}",
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(remaining)} lines remaining)")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"\n! Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would remove {len(removed)} lines, {len(remaining)} remaining")


if __name__ == "__main__":
    main()
