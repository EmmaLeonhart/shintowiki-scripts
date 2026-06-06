#!/usr/bin/env python3
"""
generate_en_labels_quickstatements.py
======================================
Renders [[QuickStatements/En labels]] from the shared dict maintained
by ``orchestrators.ops.duplicate_qids``. For every (title, qid) where
the Wikidata item lacks an English label, emit:

    Qxxx|Len|"<title without namespace prefix>"

Mainspace + ``Category:`` only — same scope blocklist as the
P11250 / P6262 generators (``Template:`` skipped).

Why this script exists
----------------------
``generate_p11250_quickstatements.py`` already emits ``Len`` lines as a
side effect when it emits a P11250 line for an item missing the en
label. But once an item already has its P11250 (or has been filtered
for namespace), the P11250 generator stops emitting both lines —
including the en-label line. This script fills the gap by checking
EVERY tracked QID for a missing en label, regardless of P11250 state.

Wikidata-side query
-------------------
Single SPARQL POST to WDQS that returns ``(item, en_label)`` rows for
every QID in one VALUES clause. Live-tested at ~4s for 5000 QIDs vs
~60s for the previous 120 batches of wbgetentities. Per CLAUDE.md:
cleanup-loop scripts query collectively (bulk SPARQL); per-page
individual queries belong only in the orchestrator ops.

Cleanup pass
------------
Lines currently on [[QuickStatements/En labels]] whose item now has
an English label on Wikidata are removed, so the page converges to
"items still needing an en label".

429 policy: any HTTP 429 from Wikidata terminates immediately (no
retries), consistent with the P11250 / P6262 generators.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (kept
for CLI parity — only one wiki write happens), ``--run-tag``.
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

QS_PAGE_TITLE = "QuickStatements/En labels"
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")

# Match QS lines like: Q12345|Len|"Some Label"
QS_LINE_RE = re.compile(r'^(Q\d+)\|Len\|"(.+)"$')

# Same blocklist as P11250 / P6262 — mainspace + Category: only.
SKIP_PREFIXES = ("Template:",)

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
QID_RE = re.compile(r"^Q\d+$")

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
    entry = f"[{timestamp}] [{severity}] generate_en_labels_quickstatements: {message}\n"
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
QuickStatements for backfilling English labels on Wikidata items that have a corresponding page on [https://shinto.miraheze.org shinto.miraheze.org] but no <code>en</code> label set yet.

Each line below sets the English label of a Wikidata item to the local page title (with the namespace prefix stripped). Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


# ─── WIKIDATA ───────────────────────────────────────────────

def fetch_en_labels(qids: list[str]) -> dict[str, "str | None"]:
    """Bulk-fetch en labels for every QID via ONE SPARQL POST.

    Returns ``{qid: en_label or None}``:
        * en label string if Wikidata has one set
        * ``None`` when the item exists but has no en label

    On query failure, returns ``{}`` — caller treats absence as
    "unknown — don't infer either way", matching the previous batched
    code's per-batch failure mode (just at whole-query granularity)."""
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

    # Default everyone to None (no en label); upgrade to the actual
    # string when we see a binding. Cross-product safety: iterate every
    # row, last non-empty value wins (in practice rdfs:label en is
    # single-valued, so this is just defensive).
    out: dict[str, "str | None"] = {q: None for q in qids}
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if qid not in out:
            continue
        val = row.get("label", {}).get("value", "").strip()
        if val:
            out[qid] = val
    return out


def title_to_label(title: str) -> str:
    """Strip a leading namespace prefix to get a Wikidata-style en label.
    "Category:Shrines in Tokyo" -> "Shrines in Tokyo"; mainspace passes
    through. Only namespaces we actually emit Len for are recognized."""
    if title.startswith("Category:"):
        return title[len("Category:"):]
    return title


def qs_escape(value: str) -> str:
    """Escape a string for inclusion in a QS v1 quoted value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def filter_existing_on_miraheze(site, titles: list[str]) -> set[str]:
    """Return the subset of `titles` that exist on shinto.miraheze.org
    as non-redirect pages.

    Per the queue plan, miraheze is the source of truth for whether
    a page exists. The orchestrator-collected state can be stale (a
    title visited last sweep may have been deleted), so this batch-
    check keeps us from emitting an en-label statement for a Wikidata
    item whose miraheze page no longer exists. Bulk-queries in
    batches of 50.
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
            existing.update(batch)  # conservative on failure
            continue
        for page in result.get("query", {}).get("pages", []):
            if page.get("missing"):
                continue
            if page.get("redirect"):
                continue
            existing.add(page["title"])
    return existing


def parse_qs_page(text: str) -> dict[str, str]:
    """Return {qid: label} for every QS Len line on the page."""
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

    # qid → list of source titles (a single QID may map from multiple
    # pages, e.g. a category whose subject and disambiguator both map
    # to the same item). Use the alphabetically-first title as the
    # canonical label source — predictable + reproducible.
    qid_to_title: dict[str, str] = {}
    for title, qid in sorted(filtered_state.items()):
        if qid not in qid_to_title:
            qid_to_title[qid] = title

    qids = sorted(qid_to_title.keys())
    print(f"Distinct QIDs: {len(qids)}")

    print("Fetching en labels from Wikidata (batched)...")
    wd_en_labels = fetch_en_labels(qids)
    fetched = sum(1 for v in wd_en_labels.values() if v is not None)
    missing = sum(1 for qid in qids if wd_en_labels.get(qid) is None and qid in wd_en_labels)
    unknown = sum(1 for qid in qids if qid not in wd_en_labels)
    print(f"  Have en label:               {fetched}")
    print(f"  Missing en label:            {missing}")
    print(f"  Unknown (fetch failed):      {unknown}")

    new_qs: dict[str, str] = {}
    for qid in qids:
        if qid not in wd_en_labels:
            continue  # unknown — don't emit anything
        if wd_en_labels[qid]:
            continue  # already has en label
        title = qid_to_title[qid]
        label = title_to_label(title)
        if not label:
            continue
        new_qs[qid] = label

    print(f"\nComputed:")
    print(f"  Need en-label QS line:       {len(new_qs)}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # Source-of-truth check: drop QS lines for pages that no longer
    # exist on miraheze. Filters ``new_qs`` only; preserved existing
    # lines aren't reconfirmed (they were valid when last emitted).
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

    preserved: dict[str, str] = {}
    removed: list[str] = []
    for qid, label in existing_qs.items():
        if qid not in wd_en_labels:
            # Unknown state — keep the line as-is.
            preserved[qid] = label
            continue
        if wd_en_labels[qid]:
            # Now has an en label — drop the line.
            removed.append(qid)
            continue
        preserved[qid] = label

    merged = {**preserved, **new_qs}
    print(f"  Preserved existing lines:    {len(preserved)}")
    print(f"  Removed (now has en label):  {len(removed)}")
    print(f"  Final en-label line count:   {len(merged)}")

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
                    f"Bot: update en-label QuickStatements "
                    f"(+{len(new_qs)}, -{len(removed)}) "
                    f"{args.run_tag}"
                ),
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(merged)} en-label lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] ({len(merged)} en-label lines)")
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
