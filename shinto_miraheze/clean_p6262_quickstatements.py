#!/usr/bin/env python3
"""
clean_p6262_quickstatements.py
===============================
Reads [[QuickStatements/P6262]] on shintowiki and removes lines whose
Wikidata item already carries the same P6262 (Fandom article ID) value.

Strategy: ONE SPARQL query that returns every (item, value) pair on
Wikidata where ``P6262`` starts with ``"shinto:"`` (the Fandom subdomain
identifier). The QS page lines are filtered locally against that result
set — no per-QID API traffic.

Mirror of clean_p11250_quickstatements.py — same shape and rationale,
only the property differs (P6262 = Fandom article ID; P11250 = Miraheze
article ID). Both use the same colon-separated value form
``shinto:Title``; the property is what discriminates the Fandom link
from the Miraheze one.

Default mode is dry-run. Use --apply to actually edit the wiki page.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry
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
# Prefix the P6262 value must start with for us to count it as "the
# same shinto.fandom.com page" — the QS page only ever generates lines
# with this prefix, and any other value on the same QID belongs to a
# different Fandom subdomain and is not relevant to our reconciliation.
P6262_PREFIX = f"{FANDOM_SUBDOMAIN}:"

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
        # Pinned policy: bail on 429, no retry. Exit 0 so the cleanup-loop
        # CI step doesn't fail — the next scheduled run picks up.
        print("   ! 429 Too Many Requests from SPARQL — terminating cleanly (next run resumes)", file=sys.stderr)
        sys.exit(0)
    resp.raise_for_status()
    return resp.json().get("results", {}).get("bindings", [])


def fetch_existing_p6262() -> dict[str, list[str]]:
    """Single SPARQL query: every (item, value) pair on Wikidata where
    P6262 starts with ``shinto:``. Returns a ``{qid: [values...]}``
    dict that the caller filters QS lines against locally.

    See clean_p11250_quickstatements.fetch_existing_p11250 for the
    design rationale — this is the P6262 mirror of that function."""
    query = f"""
SELECT ?item ?value WHERE {{
  ?item wdt:P6262 ?value .
  FILTER(STRSTARTS(?value, "{P6262_PREFIX}"))
}}
"""
    print(f"  one SPARQL query: all P6262 values starting {P6262_PREFIX!r} ...")
    bindings = sparql_query(query)
    result: dict[str, list[str]] = {}
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        value = row["value"]["value"]
        result.setdefault(qid, []).append(value)
    print(f"  got {sum(len(v) for v in result.values())} (item, value) row(s) "
          f"across {len(result)} item(s)")
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

    # FANDOM_SUNSET_DATE mirrors the canonical constant in
    # shinto_miraheze/orchestrators/ops/fandom_mirror.py. Inlined here
    # because this script runs as `python3 shinto_miraheze/X.py` (the
    # script dir is on sys.path, not the repo root, and there's no
    # shinto_miraheze/__init__.py), so the package import raised
    # ModuleNotFoundError and crashed every run. Keep the two in sync.
    import datetime as _dt
    FANDOM_SUNSET_DATE = _dt.date(2027, 1, 1)
    if _dt.datetime.utcnow().date() >= FANDOM_SUNSET_DATE:
        print(
            f"clean_p6262_quickstatements disabled: past "
            f"FANDOM_SUNSET_DATE ({FANDOM_SUNSET_DATE.isoformat()}). "
            f"Leaving the QS page untouched."
        )
        return

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    login_with_retry(site, USERNAME, PASSWORD)
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

    # Single SPARQL fetch of every P6262 value on Wikidata that starts
    # with ``shinto:``. We then filter the QS page's QIDs against this
    # global dict locally — no per-QID API traffic.
    print(f"\nFetching all P6262 ({P6262_PREFIX!r}-prefixed) values on Wikidata via SPARQL...")
    existing_p6262 = fetch_existing_p6262()

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
