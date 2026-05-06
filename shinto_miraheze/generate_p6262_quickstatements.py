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
  * Batch-query Wikidata (wbgetentities, 50 QIDs per call) for any
    existing P6262 values.
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
    entry = f"[{timestamp}] [{severity}] generate_p6262_quickstatements: {message}\n"
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
QuickStatements for syncing [https://www.wikidata.org/wiki/Property:P6262 P6262] (Fandom article ID) to Wikidata.

Each line below adds a <code>P6262</code> claim linking a Wikidata item to its corresponding page on [https://shinto.fandom.com shinto.fandom.com]. Lines are automatically added and removed by [[User:EmmaBot]].

<pre>
"""

QS_PAGE_FOOTER = "</pre>"


# ─── WIKIDATA ───────────────────────────────────────────────

def fetch_p6262(qids: list[str]) -> dict[str, list[str]]:
    """Batch-query Wikidata for existing P6262 values on each QID.

    Returns ``{qid: [P6262 values]}`` (empty list if missing/unknown).
    """
    p6262: dict[str, list[str]] = {}
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
                p6262[qid] = []
            continue

        for qid in batch:
            entity = entities.get(qid, {})
            if "missing" in entity:
                p6262[qid] = []
                continue
            claims = entity.get("claims", {}).get("P6262", [])
            values = []
            for c in claims:
                dv = c.get("mainsnak", {}).get("datavalue", {})
                if dv.get("type") == "string":
                    values.append(dv.get("value"))
            p6262[qid] = [v for v in values if v]
        time.sleep(0.5)
    return p6262


def qs_escape(value: str) -> str:
    """Escape a string for inclusion in a QS v1 quoted value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def fandom_value(title: str) -> str:
    """Return the P6262 value for a Miraheze page title. Pages mirror
    1:1 onto shinto.fandom.com under the same title."""
    return f"{FANDOM_SUBDOMAIN}:{title}"


def parse_qs_page(text: str) -> dict[str, str]:
    """Return {qid: "shinto:Title"} for every QS line on the page."""
    existing = {}
    for line in text.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            existing[m.group(1)] = f"{FANDOM_SUBDOMAIN}:{m.group(2)}"
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

    preserved: dict[str, str] = {}
    removed: list[str] = []
    for qid, expected in existing_qs.items():
        values = wd_p6262.get(qid)
        if values is None:
            preserved[qid] = expected
            continue
        if expected in values:
            removed.append(qid)
            continue
        preserved[qid] = expected

    merged = {**preserved, **new_qs}
    print(f"  Preserved existing lines:    {len(preserved)}")
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
        sys.exit(1)
    except Exception:
        log_error(f"Unhandled exception:\n{traceback.format_exc()}")
        sys.exit(1)
