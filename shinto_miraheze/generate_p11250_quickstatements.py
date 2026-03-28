#!/usr/bin/env python3
"""
generate_p11250_quickstatements.py
===================================
Walks pages in [[Category:Pages linked to Wikidata]] (including subcategories),
extracts the QID from {{wikidata link|Q…}}, checks whether the Wikidata item
already has P11250 (Miraheze article ID) pointing to shinto:<PAGENAME>, and if
not, adds a QuickStatements line to [[QuickStatements/P11250]].

Also cleans up: any QS lines on the wiki page for items that now have the
correct P11250 are removed.

* Processes up to --max-edits pages per run (default 100, stateful).
* When the full category has been processed, the state file resets so the
  next run starts a fresh sweep.

Default mode is dry-run. Use --apply to actually edit the wiki page.
"""

import argparse
import datetime
import io
import os
import re
import sys
import time
import traceback

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

CATEGORY_NAME = "Pages linked to Wikidata"
QS_PAGE_TITLE = "QuickStatements/P11250"
STATE_FILE = os.path.join(os.path.dirname(__file__), "generate_p11250_quickstatements.state")
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

WD_LINK_RE = re.compile(r'\{\{wikidata link\|(Q\d+)\}\}', re.IGNORECASE)
# Match QS lines like: Q12345|P11250|"shinto:Page Name"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

# Retry session for transient network errors (502, 503, 504, timeouts)
# NOTE: 429 (Too Many Requests) is deliberately excluded — it triggers
# immediate termination to avoid worsening rate-limit situations.
_retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://", HTTPAdapter(max_retries=_retry_strategy))


# ─── ERROR LOGGING ─────────────────────────────────────────

class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests response is received."""


def log_error(message, *, fatal=False):
    """Append a timestamped error entry to the error log file."""
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity = "FATAL" if fatal else "ERROR"
    entry = f"[{timestamp}] [{severity}] generate_p11250_quickstatements: {message}\n"
    print(f"   ! {severity}: {message}", file=sys.stderr)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def checked_get(url, **kwargs):
    """Wrapper around _http.get that checks for 429 and logs + terminates."""
    resp = _http.get(url, **kwargs)
    if resp.status_code == 429:
        log_error(
            f"429 Too Many Requests from {resp.url} — terminating immediately to avoid further rate-limit violations",
            fatal=True,
        )
        raise RateLimitError(f"429 Too Many Requests: {resp.url}")
    return resp

QS_PAGE_HEADER = """\
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P11250 P11250] (Miraheze article ID) to Wikidata.

Each line below adds a <code>P11250</code> claim linking a Wikidata item to its corresponding page on [https://shinto.miraheze.org shinto.miraheze.org]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


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

def get_category_pages(site, category_name):
    """Get all direct members of a category (all namespaces, no recursion)."""
    full_cat = f"Category:{category_name}"
    pages = []

    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": full_cat,
        "cmlimit": 500,
        "format": "json",
    }
    while True:
        resp = checked_get(
            f"https://{WIKI_URL}{WIKI_PATH}api.php",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for m in data.get("query", {}).get("categorymembers", []):
            pages.append(m["title"])
        if "continue" not in data:
            break
        params["cmcontinue"] = data["continue"]["cmcontinue"]

    return pages


def get_wikidata_p11250(qid):
    """
    Fetch P11250 values for a Wikidata item.
    Returns a list of string values, or None on error.
    """
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        resp = checked_get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        entity = resp.json().get("entities", {}).get(qid, {})
        claims = entity.get("claims", {}).get("P11250", [])
        values = []
        for claim in claims:
            dv = claim.get("mainsnak", {}).get("datavalue", {})
            if dv.get("type") == "string":
                values.append(dv["value"])
        return values
    except RateLimitError:
        raise  # must propagate — never swallow 429s
    except Exception as e:
        log_error(f"Failed to fetch P11250 for {qid}: {e}")
        return None


def parse_qs_page(text):
    """Parse existing QS page, return set of (qid, expected_value) tuples and non-QS lines."""
    existing_qs = {}  # qid -> expected_value
    header_lines = []
    in_pre = False
    found_pre = False

    for line in text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            existing_qs[m.group(1)] = f"shinto:{m.group(2)}"
        elif line.strip() == "<pre>":
            in_pre = True
            found_pre = True
        elif line.strip() == "</pre>":
            in_pre = False

    return existing_qs


# ─── MAIN ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually save the QuickStatements page (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max pages to process per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # Load state
    done = load_state(STATE_FILE)
    print(f"State: {len(done)} pages already processed")

    # Fetch category members
    print(f"Fetching [[Category:{CATEGORY_NAME}]]...")
    all_pages = get_category_pages(site, CATEGORY_NAME)
    # Deduplicate while preserving order
    seen = set()
    unique_pages = []
    for t in all_pages:
        if t not in seen:
            seen.add(t)
            unique_pages.append(t)
    all_pages = unique_pages
    print(f"Found {len(all_pages)} unique pages total")

    # Filter out already-processed
    pending = [t for t in all_pages if t not in done]
    print(f"Pending: {len(pending)} pages")

    if not pending:
        print("All pages processed — clearing state for next cycle.")
        clear_state(STATE_FILE)
        # Still do cleanup pass below
        pending = []

    batch = pending[: args.max_edits] if pending else []
    if batch:
        print(f"Processing batch of {len(batch)} pages\n")

    # ─── Process batch ──────────────────────────────────────
    new_qs = {}  # qid -> expected_value  (new lines to add)
    skipped_no_template = 0
    skipped_already_correct = 0
    skipped_error = 0

    for idx, title in enumerate(batch, 1):
        print(f"{idx}/{len(batch)}  [[{title}]]")

        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            log_error(f"Could not read page [[{title}]]: {e}")
            skipped_error += 1
            append_state(STATE_FILE, title)
            continue

        m = WD_LINK_RE.search(text)
        if not m:
            print("   - no {{wikidata link}} template, skipping")
            skipped_no_template += 1
            append_state(STATE_FILE, title)
            continue

        qid = m.group(1)
        expected_value = f"shinto:{title}"

        p11250_values = get_wikidata_p11250(qid)
        if p11250_values is None:
            skipped_error += 1
            continue

        if expected_value in p11250_values:
            print(f"   OK {qid} already has P11250={expected_value}")
            skipped_already_correct += 1
            append_state(STATE_FILE, title)
            time.sleep(0.3)
            continue

        new_qs[qid] = expected_value
        if p11250_values:
            print(f"   + {qid} has P11250={p11250_values} but not {expected_value}")
        else:
            print(f"   + {qid} missing P11250 -> {expected_value}")

        append_state(STATE_FILE, title)
        time.sleep(0.3)

    # ─── Reconcile QS page ──────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Batch results:")
    print(f"  New QuickStatements:    {len(new_qs)}")
    print(f"  Already correct:        {skipped_already_correct}")
    print(f"  No wikidata template:   {skipped_no_template}")
    print(f"  Errors (will retry):    {skipped_error}")

    # Read existing QS page
    qs_page = site.pages[QS_PAGE_TITLE]
    try:
        existing_text = qs_page.text() if qs_page.exists else ""
    except Exception:
        existing_text = ""

    existing_qs = parse_qs_page(existing_text)
    print(f"\nExisting QS lines on wiki: {len(existing_qs)}")

    # Merge: existing + new
    merged = dict(existing_qs)
    merged.update(new_qs)

    # Cleanup pass: check existing QS lines — remove any that are now correct on Wikidata
    removed = []
    for qid, expected in list(existing_qs.items()):
        if qid in new_qs:
            continue  # just added, skip check
        p11250_values = get_wikidata_p11250(qid)
        if p11250_values is not None and expected in p11250_values:
            print(f"   Removing {qid}|P11250|\"{expected}\" — already on Wikidata")
            del merged[qid]
            removed.append(qid)
            time.sleep(0.3)

    print(f"  Removed (now on Wikidata): {len(removed)}")
    print(f"  Final QS line count:       {len(merged)}")

    # Build page
    qs_lines = []
    for qid in sorted(merged.keys()):
        qs_lines.append(f'{qid}|P11250|"{merged[qid]}"')

    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if new_page_text.rstrip() == existing_text.rstrip():
        print("\nNo changes to QS page.")
        return

    if args.apply:
        try:
            qs_page.save(new_page_text,
                         summary=f"Bot: update P11250 QuickStatements (+{len(new_qs)} -{len(removed)}) {args.run_tag}")
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(merged)} total lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] ({len(merged)} lines):")
        for line in qs_lines[:10]:
            print(f"  {line}")
        if len(qs_lines) > 10:
            print(f"  ... and {len(qs_lines) - 10} more")


if __name__ == "__main__":
    try:
        main()
    except RateLimitError:
        # Already logged by checked_get / log_error — exit with error
        sys.exit(1)
    except Exception:
        log_error(f"Unhandled exception:\n{traceback.format_exc()}")
        sys.exit(1)
