#!/usr/bin/env python3
"""
generate_p6262_quickstatements.py
==================================
Renders [[QuickStatements/P6262]] from the shared dict maintained by
``orchestrators.ops.duplicate_qids``. That op records ``title -> QID``
for every page with a ``{{wikidata link|Q...}}`` template across all
four orchestrators (mainspace, category, template, miscellaneous), so
this renderer picks up Mainspace and Category: pages automatically —
the same source of truth that ``generate_p11250_quickstatements.py``
uses for the Miraheze (P11250) link, just emitted onto a different
Wikidata property.

Background. P6262 is "Fandom article ID" on Wikidata, used to link a
Wikidata item to its corresponding page on a Fandom wiki. The mirror
copies every shintowiki mainspace/category page to shinto.fandom.com
under the SAME title (see ``orchestrators/ops/fandom_mirror.py``), so
the same ``title -> qid`` mapping that drives P11250 also drives P6262
— we just emit a different property and value prefix.

For each (title, qid) in the shared state:
  * Skip ``Template:`` titles — same rationale as P11250: too many
    template-namespace items on Wikidata for blanket linking. Mainspace
    and ``Category:`` only.
  * Single SPARQL POST to WDQS that returns ``(item, p6262)`` rows for
    every QID in one VALUES clause. Live-tested at ~1s for 5000 QIDs vs
    ~60s for the previous 120 batches of wbgetentities. Per CLAUDE.md:
    cleanup-loop scripts query collectively (bulk SPARQL); per-page
    individual queries belong only in the orchestrator ops.
  * If ``shinto:<title>`` is already among the P6262 values, skip the
    line.
  * Otherwise emit ``Qxxx|P6262|"shinto:<title>"``.

Cleanup pass: any line currently on [[QuickStatements/P6262]] whose QID
already has the correct P6262 on Wikidata is removed, so the page
converges to "items still needing a Fandom link".

No per-script state file — the orchestrator ops keep the title list
fresh. First cycle after deploy has an empty page on the wiki; the QS
page grows over successive cycles as the orchestrators sweep the wiki.

429 policy: any HTTP 429 from Wikidata terminates the script
immediately (no retries), consistent with the pinned note in status.md.

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
from shinto_miraheze.qs_value import qs_escape, qs_unescape
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

QS_PAGE_TITLE = "QuickStatements/P6262"
ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")

# P6262 stores values as "<subdomain>:<page title>" — colon separator,
# matching the same convention P11250 uses on Miraheze. Both wikis
# (shinto.miraheze.org, shinto.fandom.com) use "shinto" as subdomain,
# so the value strings look identical between properties; the
# discriminator is the property itself (P11250 vs P6262).
FANDOM_SUBDOMAIN = "shinto"

# Match QS lines like: Q12345|P6262|"shinto:Page Name"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P6262\|"' + re.escape(FANDOM_SUBDOMAIN) + r':(.+)"$')

# Same blocklist as P11250 — mainspace + Category: only.
SKIP_PREFIXES = ("Template:",)

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
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
    entry = f"[{timestamp}] [{severity}] generate_p6262_quickstatements: {message}\n"
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
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P6262 P6262] (Fandom article ID) to Wikidata.

Each line below adds a <code>P6262</code> claim linking a Wikidata item to its corresponding page on [https://shinto.fandom.com shinto.fandom.com]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


# ─── WIKIDATA ───────────────────────────────────────────────

def fetch_p6262(qids: list[str]) -> dict[str, list[str]]:
    """Bulk-fetch existing P6262 values for every QID via ONE SPARQL
    POST against WDQS.

    Returns ``{qid: [P6262 values]}`` — empty list when the item has no
    P6262 (or doesn't exist on Wikidata; the wdt:P6262 OPTIONAL just
    doesn't bind in that case). On query failure returns ``{qid: []}``
    for every QID — matches the previous batched code's "treat unknown
    as empty" behavior so we don't generate bogus QS lines after a
    transient WDQS error."""
    qids = [q for q in qids if QID_RE.match(q)]
    if not qids:
        return {}

    values_clause = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?item ?p6262 WHERE {{
  VALUES ?item {{ {values_clause} }}
  OPTIONAL {{ ?item wdt:P6262 ?p6262 . }}
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
        return {q: [] for q in qids}

    p6262: dict[str, list[str]] = {q: [] for q in qids}
    for row in bindings:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if qid not in p6262:
            continue
        p_val = row.get("p6262", {}).get("value")
        if p_val and p_val not in p6262[qid]:
            p6262[qid].append(p_val)
    return p6262


def fandom_value(title: str) -> str:
    """Return the P6262 value for a Miraheze page title. Pages mirror
    1:1 onto shinto.fandom.com under the same title."""
    return f"{FANDOM_SUBDOMAIN}:{title}"


def filter_existing_on_miraheze(site, titles: list[str]) -> set[str]:
    """Return the subset of `titles` that exist on shinto.miraheze.org
    as non-redirect pages.

    Per the queue plan: miraheze is the source of truth for whether a
    page exists, even when emitting P6262 (Fandom article ID). The
    fandom mirror copies miraheze 1:1 under the same title, so a
    miraheze deletion implies the fandom copy is also stale.

    Bulk-queries in batches of 50.
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
    """Return {qid: "shinto:Title"} for every QS line on the page.

    ``qs_unescape`` is what makes this the inverse of the render below. Without it
    the captured text is still escaped and the render escapes it a second time, so
    a value's backslashes double on every run -- the bug that grew Q123999885's
    line to 1,048,643 bytes and pushed the page past MediaWiki's save ceiling.
    """
    existing = {}
    for line in text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            existing[m.group(1)] = f"{FANDOM_SUBDOMAIN}:{qs_unescape(m.group(2))}"
    return existing


def resolve_existing(existing_qs, desired, wd_values):
    """Decide what happens to each QS line already on the page.

    Returns ``(preserved, removed, repaired)``: the lines to keep with the value to
    keep them at, the QIDs whose claim is now on Wikidata, and a count of lines whose
    page value disagreed with the state file.

    **The state file is the source of truth for a QID's value**, so a preserved line
    is re-derived from ``desired`` rather than carried over from the page text. Two
    things that repairs, both seen live on 2026-09-04:

    * A value corrupted by the old double-escape. Q123999885 sat only here -- its
      page is missing on miraheze, so the existence check dropped it from ``new_qs``
      -- and nothing ever refreshed it. That is why one line and no other ran away
      to 1 MB while 12,877 neighbours stayed 130 bytes: every other line was rewritten
      from state each run, and this one was copied from the page it had just polluted.
    * A title that changed on the wiki after its line was written; the page copy would
      otherwise sit at the old title indefinitely.

    A QID the state does not know keeps the page's own value. 123 of them were on the
    page on 2026-09-04, and dropping those is a different decision from this one.
    """
    preserved: dict[str, str] = {}
    removed: list[str] = []
    repaired = 0
    for qid, on_page in existing_qs.items():
        expected = desired.get(qid, on_page)
        if expected != on_page:
            repaired += 1
        values = wd_values.get(qid)
        if values is None:
            preserved[qid] = expected
            continue
        if expected in values:
            removed.append(qid)
            continue
        preserved[qid] = expected
    return preserved, removed, repaired


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
            f"generate_p6262_quickstatements disabled: past "
            f"FANDOM_SUNSET_DATE ({FANDOM_SUNSET_DATE.isoformat()}). "
            f"No new fandom-article-ID claims will be emitted to Wikidata."
        )
        return

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

    desired: dict[str, str] = {}
    qid_to_title: dict[str, str] = {}
    for title, qid in filtered_state.items():
        desired[qid] = fandom_value(title)
        qid_to_title[qid] = title

    qids = sorted(desired.keys())
    print(f"Distinct QIDs: {len(qids)}")

    print("Fetching P6262 values from Wikidata (batched)...")
    wd_p6262 = fetch_p6262(qids)

    new_qs: dict[str, str] = {}
    already_correct = 0
    for qid, expected in desired.items():
        values = wd_p6262.get(qid, [])
        if expected in values:
            already_correct += 1
            continue
        new_qs[qid] = expected

    print(f"\nComputed:")
    print(f"  Already correct on Wikidata: {already_correct}")
    print(f"  Need P6262 QS line:          {len(new_qs)}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=ua_for(WIKI_URL))
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    # Source-of-truth check: drop QS lines for pages that no longer
    # exist on miraheze (the orchestrator-collected state can lag
    # deletes by a full sweep cycle). Applied to ``new_qs`` only —
    # preserved existing lines are left alone.
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

    preserved, removed, repaired = resolve_existing(existing_qs, desired, wd_p6262)

    merged = {**preserved, **new_qs}
    print(f"  Preserved existing lines:    {len(preserved)}")
    print(f"  Re-derived from state:       {repaired}")
    print(f"  Removed (now on Wikidata):   {len(removed)}")
    print(f"  Final P6262 line count:      {len(merged)}")

    qs_lines = [f'{qid}|P6262|"{qs_escape(merged[qid])}"' for qid in sorted(merged)]
    new_page_text = QS_PAGE_HEADER + "\n".join(qs_lines) + "\n" + QS_PAGE_FOOTER + "\n"

    if new_page_text.rstrip() == existing_text.rstrip():
        print("\nNo changes to QS page.")
        return

    if args.apply:
        try:
            qs_page.save(
                new_page_text,
                summary=(
                    f"Bot: update P6262 QuickStatements "
                    f"(+{len(new_qs)}, -{len(removed)}) "
                    f"{args.run_tag}"
                ),
            )
            print(f"\nSaved [[{QS_PAGE_TITLE}]] ({len(merged)} P6262 lines)")
            time.sleep(THROTTLE)
        except Exception as e:
            log_error(f"Failed to save [[{QS_PAGE_TITLE}]]: {e}")
    else:
        print(f"\nDRY RUN — would save [[{QS_PAGE_TITLE}]] ({len(merged)} P6262 lines)")
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
