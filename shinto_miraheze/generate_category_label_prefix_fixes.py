#!/usr/bin/env python3
"""
generate_category_label_prefix_fixes.py
========================================
Corrective backfill for the year-old category-prefix bug (queue.md
2026-07-04): the en-label pipeline used to strip the ``Category:``
prefix when applying English labels, so Wikidata items for our
category pages got bare labels ("Shrines in Tokyo" instead of
"Category:Shrines in Tokyo").

For every tracked ``(title, qid)`` where the title is a ``Category:``
page, bulk-fetch the item's current en label from WDQS. Where the
label exists but does NOT start with ``Category:``, emit a corrective
line to [[QuickStatements/Category label fixes]]:

    Qxxx|Len|"Category:<title body>"

The daily drip consumes that page via
``modern-quickstatements/fetch_category_label_fixes_from_wiki.py`` →
``category_label_fixes.txt`` → ``direct_daily_edits.py`` (wbsetlabel
overwrites, so the damaged label is replaced). This is deliberately
slow, rate-limited, and multi-year-tolerant — what matters is that the
pipeline is consistently correcting (Emma, 2026-07-04).

Cleanup pass: lines on the page whose item's label now starts with
``Category:`` are removed, so the page converges to "items still
damaged".

Only labels EQUAL to the stripped title body are corrected — a label
some human changed to something else entirely is not ours to clobber;
those are logged and skipped.

429 policy: any HTTP 429 terminates immediately (no retries), same as
the sibling generators.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (CLI
parity — one wiki write), ``--run-tag``.
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import time
import traceback

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

QS_PAGE_TITLE = "QuickStatements/Category label fixes"
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")

QS_LINE_RE = re.compile(r'^(Q\d+)\|Len\|"(.+)"$')

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
QID_RE = re.compile(r"^Q\d+$")

_retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://", HTTPAdapter(max_retries=_retry_strategy))


class RateLimitError(Exception):
    pass


def log_error(message, *, fatal=False):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity = "FATAL" if fatal else "ERROR"
    entry = f"[{timestamp}] [{severity}] generate_category_label_prefix_fixes: {message}\n"
    print(f"   ! {severity}: {message}", file=sys.stderr)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def checked_post(url, **kwargs):
    resp = _http.post(url, **kwargs)
    if resp.status_code == 429:
        log_error(
            f"429 Too Many Requests from {resp.url} — terminating immediately",
            fatal=True,
        )
        raise RateLimitError(f"429 Too Many Requests: {resp.url}")
    return resp


QS_PAGE_HEADER = """\
Corrective QuickStatements for the category-prefix bug: English labels applied from [https://shinto.miraheze.org shinto.miraheze.org] category pages historically had the <code>Category:</code> prefix stripped. Each line below resets the item's English label to the full page title. Lines are automatically added and removed by [[User:EmmaBot]]; the daily drip applies them gradually.

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


def fetch_en_labels(qids: list[str]) -> dict[str, "str | None"]:
    """Bulk-fetch en labels for every QID via ONE SPARQL POST.
    Returns {qid: label-or-None}; {} on query failure (caller treats
    absence as unknown)."""
    qids = [q for q in qids if QID_RE.match(q)]
    if not qids:
        return {}
    values_clause = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?item ?label WHERE {{
  VALUES ?item {{ {values_clause} }}
  OPTIONAL {{ ?item rdfs:label ?label . FILTER(LANG(?label) = "en") }}
}}
"""
    try:
        resp = checked_post(
            SPARQL_ENDPOINT,
            data={"query": query, "format": "json"},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/sparql-results+json",
            },
            timeout=180,
        )
        resp.raise_for_status()
        bindings = resp.json().get("results", {}).get("bindings", [])
    except RateLimitError:
        raise
    except Exception as e:
        log_error(f"SPARQL query failed: {e}")
        return {}

    out: dict[str, "str | None"] = {q: None for q in qids}
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if qid not in out:
            continue
        val = row.get("label", {}).get("value", "").strip()
        if val:
            out[qid] = val
    return out


def qs_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def parse_qs_page(text: str) -> dict[str, str]:
    existing = {}
    for line in text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            existing[m.group(1)] = m.group(2)
    return existing


def load_state() -> dict[str, str]:
    if not os.path.exists(STATE_FILE):
        print(f"State file not found: {STATE_FILE} — orchestrators haven't populated it yet.")
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log_error(f"Could not read {STATE_FILE}: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually save the QuickStatements page (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=1,
                        help="CLI parity; only one page is written.")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    state = load_state()
    if not state:
        print("No tracked titles; nothing to do.")
        return

    # Category: pages only. First title wins per QID (sorted = reproducible).
    qid_to_title: dict[str, str] = {}
    for title, qid in sorted(state.items()):
        if title.startswith("Category:") and qid not in qid_to_title:
            qid_to_title[qid] = title
    print(f"Tracked Category: pages: {len(qid_to_title)}")
    if not qid_to_title:
        print("No category pages tracked; nothing to do.")
        return

    qids = sorted(qid_to_title.keys())
    print("Fetching en labels from Wikidata (bulk SPARQL)...")
    wd_en_labels = fetch_en_labels(qids)

    new_fixes: dict[str, str] = {}
    diverged: list[str] = []
    for qid in qids:
        if qid not in wd_en_labels:
            continue  # unknown — don't emit
        label = wd_en_labels[qid]
        if label is None:
            continue  # no label — the en-labels pipeline's job, not ours
        title = qid_to_title[qid]
        if label == title:
            continue  # already correct
        body = title[len("Category:"):]
        if label == body:
            new_fixes[qid] = title  # the exact bug signature — fix it
        else:
            diverged.append(qid)  # human-edited label; not ours to clobber

    print(f"  Damaged (label == stripped title): {len(new_fixes)}")
    print(f"  Diverged (label != title, != stripped title; skipped): {len(diverged)}")
    if diverged:
        print(f"    e.g. {', '.join(diverged[:5])}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    qs_page = site.pages[QS_PAGE_TITLE]
    try:
        existing_text = qs_page.text() if qs_page.exists else ""
    except Exception:
        existing_text = ""
    existing_qs = parse_qs_page(existing_text)
    print(f"Existing fix lines on wiki: {len(existing_qs)}")

    preserved: dict[str, str] = {}
    removed: list[str] = []
    for qid, label in existing_qs.items():
        if qid not in wd_en_labels:
            preserved[qid] = label  # unknown state — keep
            continue
        current = wd_en_labels[qid]
        if current and current.startswith("Category:"):
            removed.append(qid)  # fixed — drop the line
            continue
        preserved[qid] = label

    merged = {**preserved, **new_fixes}
    print(f"  Preserved existing lines:   {len(preserved)}")
    print(f"  Removed (now fixed):        {len(removed)}")
    print(f"  Final fix line count:       {len(merged)}")

    qs_lines = [f'{qid}|Len|"{qs_escape(merged[qid])}"' for qid in sorted(merged)]
    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if new_page_text.rstrip() == existing_text.rstrip():
        print("\nNo changes to QS page.")
        return

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=(
                    f"Bot: update Category-label-prefix fixes "
                    f"(+{len(new_fixes)}, -{len(removed)}) "
                    f"{args.run_tag}"
                ),
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(merged)} fix lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] ({len(merged)} fix lines)")
        for line in qs_lines[:10]:
            print(f"  {line}")
        if len(qs_lines) > 10:
            print(f"  ... and {len(qs_lines) - 10} more")


if __name__ == "__main__":
    try:
        main()
    except RateLimitError:
        sys.exit(0)
    except Exception:
        log_error(f"Unhandled exception:\n{traceback.format_exc()}")
        sys.exit(1)
