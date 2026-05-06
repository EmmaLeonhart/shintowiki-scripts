#!/usr/bin/env python3
"""
clean_p6262_quickstatements.py
===============================
Reads [[QuickStatements/P6262]] on shintowiki and bulk-checks all QS lines
against Wikidata using SPARQL. If a Wikidata item already has the correct
P6262 (Fandom article ID) value, the line is removed from the page.

Mirror of clean_p11250_quickstatements.py — same shape, only the
property differs (P6262 vs P11250). Both use the same colon-separated
value form ``shinto:Title``; the property itself is what discriminates
the Fandom link from the Miraheze one. See clean_p11250_quickstatements
for the design rationale.

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
THROTTLE = 2.5

QS_PAGE_TITLE = "QuickStatements/P6262"

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

FANDOM_SUBDOMAIN = "shinto"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P6262\|"' + re.escape(FANDOM_SUBDOMAIN) + r':(.+)"$')

QS_PAGE_HEADER = """\
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P6262 P6262] (Fandom article ID) to Wikidata.

Each line below adds a <code>P6262</code> claim linking a Wikidata item to its corresponding page on [https://shinto.fandom.com shinto.fandom.com]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SPARQL_BATCH_SIZE = 200

_retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://", HTTPAdapter(max_retries=_retry_strategy))


def sparql_query(query):
    resp = _http.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        timeout=120,
    )
    if resp.status_code == 429:
        print("   ! FATAL: 429 Too Many Requests from SPARQL — terminating", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json().get("results", {}).get("bindings", [])


def bulk_check_p6262(qids):
    result = {}
    batches = [qids[i:i + SPARQL_BATCH_SIZE] for i in range(0, len(qids), SPARQL_BATCH_SIZE)]
    for batch_num, batch in enumerate(batches, 1):
        print(f"  SPARQL batch {batch_num}/{len(batches)} ({len(batch)} QIDs)...")
        values_clause = " ".join(f"wd:{qid}" for qid in batch)
        query = f"""
SELECT ?item ?value WHERE {{
  VALUES ?item {{ {values_clause} }}
  ?item wdt:P6262 ?value .
}}
"""
        try:
            bindings = sparql_query(query)
            for row in bindings:
                qid = row["item"]["value"].rsplit("/", 1)[-1]
                value = row["value"]["value"]
                result.setdefault(qid, []).append(value)
        except Exception as e:
            print(f"   ! SPARQL batch {batch_num} failed: {e}", file=sys.stderr)
        if batch_num < len(batches):
            time.sleep(2)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Remove completed P6262 QuickStatements from the wiki page using SPARQL bulk check."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit the QS page (default is dry-run).")
    parser.add_argument("--max-checks", type=int, default=0,
                        help="Ignored (CLI parity). All lines are checked via SPARQL.")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    qs_page = site.pages[QS_PAGE_TITLE]
    try:
        existing_text = qs_page.text() if qs_page.exists else ""
    except Exception as e:
        print(f"ERROR reading [[{QS_PAGE_TITLE}]]: {e}")
        return

    qs_entries = {}
    for line in existing_text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            qs_entries[m.group(1)] = f"{FANDOM_SUBDOMAIN}:{m.group(2)}"

    print(f"Found {len(qs_entries)} QS lines on [[{QS_PAGE_TITLE}]]")
    if not qs_entries:
        print("Nothing to check.")
        return

    print(f"\nBulk checking {len(qs_entries)} items via SPARQL...")
    existing_p6262 = bulk_check_p6262(list(qs_entries.keys()))
    print(f"SPARQL found P6262 values on {len(existing_p6262)} items")

    removed = []
    for qid, expected in qs_entries.items():
        wd_values = existing_p6262.get(qid, [])
        if expected in wd_values:
            print(f"  REMOVE {qid} — P6262=\"{expected}\" already on Wikidata")
            removed.append(qid)

    print(f"\n{'='*50}")
    print(f"Total QS lines:  {len(qs_entries)}")
    print(f"Already done:    {len(removed)}")
    print(f"Still needed:    {len(qs_entries) - len(removed)}")

    if not removed:
        print("No lines to remove.")
        return

    removed_set = set(removed)
    remaining = {qid: val for qid, val in qs_entries.items() if qid not in removed_set}
    qs_lines = [f'{qid}|P6262|"{remaining[qid]}"' for qid in sorted(remaining.keys())]
    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=f"Bot: remove {len(removed)} completed P6262 QuickStatements (SPARQL bulk check) {args.run_tag}",
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(remaining)} lines remaining)")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"\n! Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would remove {len(removed)} lines, {len(remaining)} remaining")


if __name__ == "__main__":
    main()
