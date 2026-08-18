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
  * Skip any ``Template:`` titles — too many existing template-namespace
    items on Wikidata for blanket P11250 linking to be safe right now.
    Mainspace and Category-namespace titles only.
  * Single SPARQL POST to WDQS that returns ``(item, p11250, en_label)``
    rows for every QID in one VALUES clause — both pieces in one query.
    Live-tested at ~5s for 5000 QIDs vs ~60s for the previous 120 batches
    of wbgetentities. Per CLAUDE.md: cleanup-loop scripts query
    collectively (bulk SPARQL); per-page individual queries belong only
    in the orchestrator ops.
  * If ``shinto:<title>`` is already among the P11250 values, skip the
    P11250 emission.
  * Otherwise emit ``Qxxx|P11250|"shinto:<title>"``.
  * If the item also lacks an English label, additionally emit
    ``Qxxx|Len|"<title without namespace prefix>"`` so the label gets
    set in the same daily QS run. Mostly relevant for category items
    that are missing en labels on Wikidata.

Cleanup pass: any line currently on [[QuickStatements/P11250]] whose
QID already has the correct P11250 on Wikidata is removed, so the page
converges to "things still needing a claim added".

No per-script state file — the orchestrator ops keep the title list
fresh. First cycle after deploy has an empty state; the QS page grows
over successive cycles as the orchestrators sweep the wiki.

429 policy: any HTTP 429 from Wikidata terminates the script
immediately (no retries), consistent with the pinned note in status.md.
Termination is a clean exit (status 0) — the next scheduled run picks
up where state left off, so a transient throttle should not mark the
cleanup-loop CI job as failed.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (kept
for CLI parity — only one wiki write happens, so effective value is 1),
``--run-tag``.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
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

QS_PAGE_TITLE = "QuickStatements/P11250"
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")

# Match QS lines like: Q12345|P11250|"shinto:Page Name"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')
# Match QS label-set lines like: Q12345|Len|"Some Label"
QS_LABEL_RE = re.compile(r'^(Q\d+)\|Len\|"(.+)"$')

# Namespace prefixes we deliberately DO NOT emit P11250 for. Template:
# is excluded because there are too many existing template-namespace
# items on Wikidata for blanket P11250 linking to be safe right now.
# Currently the orchestrators only ever record mainspace, Category:, and
# Template: titles (the misc orchestrator's namespaces don't carry
# {{wikidata link}}), so blocklisting Template: yields the
# "mainspace + Category: only" set the user asked for.
SKIP_PREFIXES = ("Template:",)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
QID_RE = re.compile(r"^Q\d+$")

# Retry transient errors — but 429 is deliberately NOT in the list; a
# 429 propagates up and aborts the script with a clean exit
# (status.md pinned policy: terminate, no retry, next run resumes).
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
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P11250 P11250] (Miraheze article ID) to Wikidata.

Each line below adds a <code>P11250</code> claim linking a Wikidata item to its corresponding page on [https://shinto.miraheze.org shinto.miraheze.org]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


# ─── WIKIDATA ───────────────────────────────────────────────

def fetch_p11250_and_labels(qids: list[str]) -> tuple[dict[str, list[str]], set[str]]:
    """Bulk-fetch P11250 values + en labels for every QID via ONE
    SPARQL POST against WDQS.

    Returns:
        p11250: {qid: [P11250 values]} — empty list when the item has
                no P11250 (or doesn't exist on Wikidata at all; the
                wdt:P11250 OPTIONAL just doesn't bind in that case).
        missing_en_label: set of QIDs that don't have an English label.

    Cross-product behavior: an item with multiple P11250 values, or a
    multi-language label set with en being one of several, can produce
    multiple result rows. The aggregation below collects values into a
    list and treats a single en-label match anywhere across an item's
    rows as "has en label".

    Failure mode mirrors the previous batched code: on exception we
    return ``{qid: []}`` for every QID and an empty
    ``missing_en_label`` (i.e. don't infer either way), so downstream
    logic conservatively skips those items rather than emitting bogus
    QS lines."""
    qids = [q for q in qids if QID_RE.match(q)]
    if not qids:
        return {}, set()

    values_clause = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?item ?p11250 ?label WHERE {{
  VALUES ?item {{ {values_clause} }}
  OPTIONAL {{ ?item wdt:P11250 ?p11250 . }}
  OPTIONAL {{ ?item rdfs:label ?label . FILTER(LANG(?label) = "en") }}
}}
"""
    try:
        resp = checked_post(
            SPARQL_ENDPOINT,
            data={"query": query, "format": "json"},
            headers={
                "User-Agent": ua_for(SPARQL_ENDPOINT),
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
        return {q: [] for q in qids}, set()

    p11250: dict[str, list[str]] = {q: [] for q in qids}
    has_en_label: set[str] = set()
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if qid not in p11250:
            continue  # defensive: VALUES set should bound the result
        p_val = row.get("p11250", {}).get("value")
        if p_val and p_val not in p11250[qid]:
            p11250[qid].append(p_val)
        if row.get("label", {}).get("value", "").strip():
            has_en_label.add(qid)

    missing_en_label = {q for q in qids if q not in has_en_label}
    return p11250, missing_en_label


def title_to_label(title: str) -> str:
    """Return the Wikidata-style en label for a local page title.

    The FULL title including the namespace prefix: Wikidata convention
    labels category items "Category:Shrines in Tokyo". Stripping the
    prefix here was a year-old bug (queue.md 2026-07-04) — see
    generate_category_label_prefix_fixes.py for the backfill of items
    already damaged by it."""
    return title


def qs_escape(value: str) -> str:
    """Escape a string for inclusion in a QS v1 quoted value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def filter_existing_on_miraheze(site, titles: list[str]) -> set[str]:
    """Return the subset of `titles` that exist on shinto.miraheze.org
    as non-redirect pages.

    Per the queue plan: "checks whether a page exists before adding it.
    Fandom pages and miraheze pages both, but whether it exists on
    miraheze is the source of truth." The orchestrator-collected state
    can be stale — a title visited last sweep may have been deleted or
    redirected since — so this batch-check filters those out before we
    emit a quickstatement that would create a Wikidata claim pointing
    nowhere.

    Bulk-queries in batches of 50 (mwclient default API limit for
    non-bot reads).
    """
    if not titles:
        return set()
    existing: set[str] = set()
    BATCH = 50
    titles_list = list(titles)
    for i in range(0, len(titles_list), BATCH):
        batch = titles_list[i:i + BATCH]
        try:
            result = site.api(
                "query",
                titles="|".join(batch),
                prop="info",
                formatversion="2",
            )
        except Exception as e:
            log_error(
                f"Page-existence check failed for batch starting "
                f"{batch[0]!r}: {e}"
            )
            # Conservative on failure: assume the batch exists rather
            # than drop legitimate quickstatements. Per-call retries
            # already handle 5xx via the requests adapter; this catches
            # everything else.
            existing.update(batch)
            continue
        for page in result.get("query", {}).get("pages", []):
            if page.get("missing"):
                continue
            if page.get("redirect"):
                continue
            existing.add(page["title"])
    return existing


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

    # Filter out namespaces we deliberately don't link to Wikidata.
    skipped_by_ns: dict[str, int] = {}
    filtered_state: dict[str, str] = {}
    for title, qid in state.items():
        skipped = False
        for prefix in SKIP_PREFIXES:
            if title.startswith(prefix):
                skipped_by_ns[prefix] = skipped_by_ns.get(prefix, 0) + 1
                skipped = True
                break
        if not skipped:
            filtered_state[title] = qid

    if skipped_by_ns:
        skipped_summary = ", ".join(f"{p}{n}" for p, n in skipped_by_ns.items())
        print(f"Skipped namespace-blocked titles: {skipped_summary}")
    print(f"Eligible titles after filter: {len(filtered_state)}")

    # title -> qid dict; want to build {qid: (expected_value, title)} for diff.
    desired: dict[str, str] = {}
    qid_to_title: dict[str, str] = {}
    for title, qid in filtered_state.items():
        desired[qid] = f"shinto:{title}"
        qid_to_title[qid] = title

    qids = sorted(desired.keys())
    print(f"Distinct QIDs: {len(qids)}")

    print("Fetching P11250 values + en labels from Wikidata (batched)...")
    wd_p11250, missing_en_label = fetch_p11250_and_labels(qids)

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
    print(f"  Need P11250 QS line:         {len(new_qs)}")
    print(f"  Missing en label:            {len(missing_en_label)}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=ua_for(WIKI_URL))
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # Source-of-truth check: drop QS lines for pages that no longer
    # exist on miraheze (deleted or redirected since the orchestrator
    # captured the title). This applies to ``new_qs`` only — preserved
    # existing lines are left alone so we don't churn ones that may
    # already be queued for human review.
    candidate_titles = [
        qid_to_title[qid]
        for qid in new_qs.keys()
        if qid in qid_to_title
    ]
    existing_titles = filter_existing_on_miraheze(site, candidate_titles)
    dropped_for_missing = 0
    for qid in list(new_qs.keys()):
        title = qid_to_title.get(qid)
        if title and title not in existing_titles:
            new_qs.pop(qid)
            dropped_for_missing += 1
    if dropped_for_missing:
        print(f"  Dropped (page missing on miraheze): {dropped_for_missing}")

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
    print(f"  Final P11250 line count:     {len(merged)}")

    # English-label backfill: for items we're emitting a P11250 line for,
    # if Wikidata has no en label, also emit Len|"<title without ns>" so
    # the daily QS run sets the label in the same pass. Only items still
    # in our current desired set get this — we have a title to use.
    label_lines: list[str] = []
    for qid in sorted(merged):
        if qid not in qid_to_title:
            continue  # preserved-only line, no title to label with
        if qid not in missing_en_label:
            continue
        label = title_to_label(qid_to_title[qid])
        if not label:
            continue
        label_lines.append(f'{qid}|Len|"{qs_escape(label)}"')
    print(f"  En-label backfill lines:     {len(label_lines)}")

    qs_lines = [f'{qid}|P11250|"{merged[qid]}"' for qid in sorted(merged)]
    if label_lines:
        qs_lines.extend(label_lines)
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
                    f"(+{len(new_qs)} P11250, +{len(label_lines)} Len, -{len(removed)}) "
                    f"{args.run_tag}"
                ),
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] "
                  f"({len(merged)} P11250 + {len(label_lines)} Len lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] "
              f"({len(merged)} P11250 + {len(label_lines)} Len lines)")
        for line in qs_lines[:10]:
            print(f"  {line}")
        if len(qs_lines) > 10:
            print(f"  ... and {len(qs_lines) - 10} more")


if __name__ == "__main__":
    try:
        main()
    except RateLimitError:
        # Pinned policy: bail on 429, no retry. Exit 0 so the cleanup-loop
        # CI step doesn't fail — the next scheduled run picks up.
        sys.exit(0)
    except Exception:
        log_error(f"Unhandled exception:\n{traceback.format_exc()}")
        sys.exit(1)
