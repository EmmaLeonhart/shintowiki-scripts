#!/usr/bin/env python3
"""
clean_p11250_quickstatements.py
================================
Reads [[QuickStatements/P11250]] on shintowiki and removes lines whose
Wikidata item already carries the same P11250 value.

Strategy: ONE SPARQL query that returns every (item, value) pair on
Wikidata where ``P11250`` starts with ``"shinto:"``. The QS page lines
are filtered locally against that result set — no per-QID API traffic.

This replaces an earlier approach that batched the QS page's QIDs into
groups of 200 and issued one SPARQL query per batch (~30 batches for
~6000 lines). When WDQS was under load, individual batch queries took
30-60 seconds each, so the step routinely ran 25+ minutes wall clock
for what is fundamentally a set-difference computation. One query that
returns the global ``shinto:``-prefixed P11250 set (a few hundred rows
at most, bounded by the size of our own QS page over time) does the
same work in seconds.

Per CLAUDE.md: nothing outside the orchestrator ops should be doing
per-QID Wikidata API calls. SPARQL set-fetch + local filter is the
right shape for this kind of bulk reconciliation.

Default mode is dry-run. Use --apply to actually edit the wiki page.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.qs_value import qs_escape, qs_unescape
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
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

QS_PAGE_TITLE = "QuickStatements/P11250"


QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')

QS_PAGE_HEADER = """\
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P11250 P11250] (Miraheze article ID) to Wikidata.

Each line below adds a <code>P11250</code> claim linking a Wikidata item to its corresponding page on [https://shinto.miraheze.org shinto.miraheze.org]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
# Prefix the P11250 value must start with for us to count it as "the
# same shintowiki page" — the QS page only ever generates lines with
# this prefix, so any other value on the same QID is from a different
# Miraheze wiki and not relevant to our reconciliation.
P11250_PREFIX = "shinto:"

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

def sparql_query(query):
    """Run a SPARQL query against Wikidata Query Service. Returns list of bindings."""
    resp = _http.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={"User-Agent": ua_for(SPARQL_ENDPOINT), "Accept": "application/sparql-results+json"},
        timeout=120,
    )
    if resp.status_code == 429:
        # Pinned policy: bail on 429, no retry. Exit 0 so the cleanup-loop
        # CI step doesn't fail — the next scheduled run picks up.
        print("   ! 429 Too Many Requests from SPARQL — terminating cleanly (next run resumes)", file=sys.stderr)
        sys.exit(0)
    resp.raise_for_status()
    return resp.json().get("results", {}).get("bindings", [])


def fetch_existing_p11250() -> dict[str, list[str]]:
    """Single SPARQL query: every (item, value) pair on Wikidata where
    P11250 starts with ``shinto:``. Returns a ``{qid: [values...]}``
    dict that the caller filters QS lines against locally.

    The result set is bounded by the number of Wikidata items that
    already point at a shintowiki page — at most a small multiple of
    the QS page's own size, well under WDQS's 50k-row response limit
    and typical query-time limit."""
    query = f"""
SELECT ?item ?value WHERE {{
  ?item wdt:P11250 ?value .
  FILTER(STRSTARTS(?value, "{P11250_PREFIX}"))
}}
"""
    print(f"  one SPARQL query: all P11250 values starting {P11250_PREFIX!r} ...")
    bindings = sparql_query(query)
    result: dict[str, list[str]] = {}
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        value = row["value"]["value"]
        result.setdefault(qid, []).append(value)
    print(f"  got {sum(len(v) for v in result.values())} (item, value) row(s) "
          f"across {len(result)} item(s)")
    return result


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove completed P11250 QuickStatements from the wiki page using SPARQL bulk check."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit the QS page (default is dry-run).")
    parser.add_argument("--max-checks", type=int, default=0,
                        help="Ignored (kept for CLI compatibility). All lines are checked via SPARQL.")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=ua_for(WIKI_URL))
    login_with_retry(site, USERNAME, PASSWORD)
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
            qs_entries[m.group(1)] = f"shinto:{qs_unescape(m.group(2))}"

    print(f"Found {len(qs_entries)} QS lines on [[{QS_PAGE_TITLE}]]")

    if not qs_entries:
        print("Nothing to check.")
        return

    # Single SPARQL fetch of every P11250 value on Wikidata that starts
    # with ``shinto:``. We then filter the QS page's QIDs against this
    # global dict locally — no per-QID API traffic.
    print(f"\nFetching all P11250 ({P11250_PREFIX!r}-prefixed) values on Wikidata via SPARQL...")
    existing_p11250 = fetch_existing_p11250()

    # Determine which lines to remove
    removed = []
    for qid, expected in qs_entries.items():
        wd_values = existing_p11250.get(qid, [])
        if expected in wd_values:
            print(f"  REMOVE {qid} — P11250=\"{expected}\" already on Wikidata")
            removed.append(qid)

    print(f"\n{'='*50}")
    print(f"Total QS lines:  {len(qs_entries)}")
    print(f"Already done:    {len(removed)}")
    print(f"Still needed:    {len(qs_entries) - len(removed)}")

    if not removed:
        print("No lines to remove.")
        return

    # Rebuild page without removed lines
    removed_set = set(removed)
    remaining = {qid: val for qid, val in qs_entries.items() if qid not in removed_set}
    qs_lines = []
    for qid in sorted(remaining.keys()):
        qs_lines.append(f'{qid}|P11250|"{qs_escape(remaining[qid])}"')

    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=f"Bot: remove {len(removed)} completed P11250 QuickStatements (SPARQL bulk check) {args.run_tag}",
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(remaining)} lines remaining)")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"\n! Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would remove {len(removed)} lines, {len(remaining)} remaining")


if __name__ == "__main__":
    main()
