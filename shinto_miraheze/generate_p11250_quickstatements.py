#!/usr/bin/env python3
"""
generate_p11250_quickstatements.py
===================================
Renders [[QuickStatements/P11250]] from the shared dict maintained by
``orchestrators.ops.duplicate_qids``. That op records ``title -> QID``
for every page with a ``{{wikidata link|Q...}}`` template across ALL
four orchestrators (mainspace, category, template, miscellaneous), so
this renderer picks up Template:/Category:/etc. pages automatically —
covering the Queued-3 ask to extend P11250 linking beyond mainspace
without a separate walk.

For each (title, qid) in the shared state:
  * Batch-query Wikidata (wbgetentities, 50 QIDs per call) for
    existing P11250 values.
  * If ``shinto:<title>`` is already among the P11250 values, skip.
  * Otherwise emit ``Qxxx|P11250|"shinto:<title>"``.

Cleanup pass: any line currently on [[QuickStatements/P11250]] whose
QID already has the correct P11250 on Wikidata is removed, so the page
converges to "things still needing a claim added".

No per-script state file — the orchestrator ops keep the title list
fresh. First cycle after deploy has an empty state; the QS page grows
over successive cycles as the orchestrators sweep the wiki.

429 policy: any HTTP 429 from Wikidata terminates the script
immediately (no retries), consistent with the pinned note in status.md.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (kept
for CLI parity — only one wiki write happens, so effective value is 1),
``--run-tag``.
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
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")

# Match QS lines like: Q12345|P11250|"shinto:Page Name"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WD_API = "https://www.wikidata.org/w/api.php"

# Retry transient errors — but 429 is deliberately NOT in the list; a
# 429 propagates up and aborts the script (status.md pinned policy).
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
    pass


def log_error(message, *, fatal=False):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity = "FATAL" if fatal else "ERROR"
    entry = f"[{timestamp}] [{severity}] generate_p11250_quickstatements: {message}\n"
    print(f"   ! {severity}: {message}", file=sys.stderr)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def checked_get(url, **kwargs):
    resp = _http.get(url, **kwargs)
    if resp.status_code == 429:
        log_error(
            f"429 Too Many Requests from {resp.url} — terminating immediately",
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


# ─── WIKIDATA ───────────────────────────────────────────────

def fetch_p11250_batch(qids: list[str]) -> dict[str, list[str]]:
    """Return {qid: [P11250 values]} for the given QIDs, 50 at a time."""
    results: dict[str, list[str]] = {}
    for i in range(0, len(qids), 50):
        batch = qids[i : i + 50]
        try:
            resp = checked_get(
                WD_API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "props": "claims",
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
        except RateLimitError:
            raise
        except Exception as e:
            log_error(f"wbgetentities batch failed ({batch[0]}...): {e}")
            for qid in batch:
                results[qid] = []  # unknown — treat as "claim not present"
            continue

        for qid in batch:
            entity = entities.get(qid, {})
            if "missing" in entity:
                results[qid] = []
                continue
            claims = entity.get("claims", {}).get("P11250", [])
            values = []
            for c in claims:
                dv = c.get("mainsnak", {}).get("datavalue", {})
                if dv.get("type") == "string":
                    values.append(dv.get("value"))
            results[qid] = [v for v in values if v]
        time.sleep(0.5)
    return results


def parse_qs_page(text: str) -> dict[str, str]:
    """Return {qid: "shinto:Title"} for every QS line on the page."""
    existing = {}
    for line in text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            existing[m.group(1)] = f"shinto:{m.group(2)}"
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


# ─── MAIN ───────────────────────────────────────────────────

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

    print(f"Tracked titles: {len(state)}")

    # title -> qid dict; want to build {qid: expected_value} for diff.
    desired: dict[str, str] = {}
    for title, qid in state.items():
        desired[qid] = f"shinto:{title}"

    qids = sorted(desired.keys())
    print(f"Distinct QIDs: {len(qids)}")

    print("Fetching P11250 values from Wikidata (batched)...")
    wd_p11250 = fetch_p11250_batch(qids)

    new_qs: dict[str, str] = {}
    already_correct = 0
    for qid, expected in desired.items():
        values = wd_p11250.get(qid, [])
        if expected in values:
            already_correct += 1
            continue
        new_qs[qid] = expected

    print(f"\nComputed:")
    print(f"  Already correct on Wikidata: {already_correct}")
    print(f"  Need QS line:                {len(new_qs)}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    qs_page = site.pages[QS_PAGE_TITLE]
    try:
        existing_text = qs_page.text() if qs_page.exists else ""
    except Exception:
        existing_text = ""

    existing_qs = parse_qs_page(existing_text)
    print(f"Existing QS lines on wiki:     {len(existing_qs)}")

    # Cleanup: any existing QS line for a QID that now has the right
    # P11250 on Wikidata can be dropped.
    preserved: dict[str, str] = {}
    removed: list[str] = []
    for qid, expected in existing_qs.items():
        values = wd_p11250.get(qid)
        if values is None:
            # QID not in our current set — preserve the existing line
            # rather than silently drop it; it might still be needed.
            preserved[qid] = expected
            continue
        if expected in values:
            removed.append(qid)
            continue
        preserved[qid] = expected

    merged = {**preserved, **new_qs}
    print(f"  Preserved existing lines:    {len(preserved)}")
    print(f"  Removed (now on Wikidata):   {len(removed)}")
    print(f"  Final QS line count:         {len(merged)}")

    qs_lines = [f'{qid}|P11250|"{merged[qid]}"' for qid in sorted(merged)]
    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if new_page_text.rstrip() == existing_text.rstrip():
        print("\nNo changes to QS page.")
        return

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=(
                    f"Bot: update P11250 QuickStatements "
                    f"(+{len(new_qs)} -{len(removed)}) {args.run_tag}"
                ),
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(merged)} lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] ({len(merged)} lines)")
        for line in qs_lines[:10]:
            print(f"  {line}")
        if len(qs_lines) > 10:
            print(f"  ... and {len(qs_lines) - 10} more")


if __name__ == "__main__":
    try:
        main()
    except RateLimitError:
        sys.exit(1)
    except Exception:
        log_error(f"Unhandled exception:\n{traceback.format_exc()}")
        sys.exit(1)
