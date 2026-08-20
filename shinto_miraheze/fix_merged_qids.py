#!/usr/bin/env python3
"""
fix_merged_qids.py
===================
Reads the live [[QuickStatements/P11250]] page on shintowiki, extracts every
``Qxxx|P11250|"shinto:Page Title"`` line, and asks Wikidata which of those
QIDs are now redirects (i.e. have been merged into another item).

For each merged QID, fetches the referenced shintowiki page and rewrites
references to the old QID (``{{wikidata link|Qold}}``, ``WD=Qold``,
``qid=Qold``) to the merge target, then saves.

Wikidata-side query
-------------------
Issues ONE SPARQL POST against WDQS with every QID from the QS page in a
single ``VALUES`` clause, asking for ``?old owl:sameAs ?new`` matches.
Live-tested at ~1.3s for 6000 QIDs vs the previous ~120 batched
action=query roundtrips at ~60s. Per CLAUDE.md: cleanup-loop scripts
process collectively, so collective bulk SPARQL is the right shape;
per-page individual queries belong only in the orchestrator ops.

Runs in CI on the EmmaBot schedule — uses the standard
``WIKI_USERNAME`` / ``WIKI_PASSWORD`` environment variables. Standard
``--apply``, ``--max-edits``, ``--run-tag`` flags. Default is dry-run.

To run locally under your own account, pass ``--local``. That ignores the
env vars and prompts for username + password on the console. Example:

    python shinto_miraheze/fix_merged_qids.py --local --apply \
        --max-edits 20 --run-tag "[local]"
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
import getpass
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

QS_PAGE_TITLE = "QuickStatements/P11250"

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"

QS_LINE_RE = re.compile(r'^\s*(Q\d+)\s*\|\s*P\d+\s*\|\s*"shinto:(.+?)"\s*$')
QID_RE = re.compile(r'^Q\d+$')


# ─── WIKIDATA REDIRECT LOOKUP ──────────────────────────────

def resolve_redirects(qids):
    """Ask Wikidata which QIDs are now redirects. Returns
    ``{old_qid: new_qid}`` for the subset that have been merged.

    Single SPARQL POST: every QID goes into one ``VALUES`` clause and
    matches against ``owl:sameAs`` to find merge targets. Live-tested at
    1.3s for 6000 QIDs (Q1..Q6000 sample → 40 redirects). Body size
    grows ~9 bytes/QID, comfortably under WDQS's POST limit.

    POST (not GET) so a 6000-QID body doesn't blow the URL length cap.
    Bail on 429 per the standing wiki policy."""
    qids = list(qids)
    if not qids:
        return {}

    values_clause = " ".join(f"wd:{q}" for q in qids if QID_RE.match(q))
    query = f"""
SELECT ?old ?new WHERE {{
  VALUES ?old {{ {values_clause} }}
  ?old owl:sameAs ?new .
}}
"""
    try:
        resp = requests.post(
            SPARQL_ENDPOINT,
            data={"query": query, "format": "json"},
            headers={
                "User-Agent": ua_for(SPARQL_ENDPOINT),
                "Accept": "application/sparql-results+json",
            },
            timeout=120,
        )
    except Exception as e:
        print(f"  [warn] SPARQL request failed: {e}")
        return {}
    if resp.status_code == 429:
        print("  [bail] HTTP 429 from WDQS; stopping.")
        sys.exit(0)
    if not resp.ok:
        print(f"  [warn] SPARQL HTTP {resp.status_code}: {resp.text[:200]}")
        return {}

    mapping: dict[str, str] = {}
    for row in resp.json().get("results", {}).get("bindings", []):
        old = row["old"]["value"].rsplit("/", 1)[-1]
        new = row["new"]["value"].rsplit("/", 1)[-1]
        if QID_RE.match(old) and QID_RE.match(new):
            mapping[old] = new
    return mapping


# ─── PAGE REWRITING ────────────────────────────────────────

def rewrite_qid(text, old_qid, new_qid):
    """
    Replace occurrences of old_qid with new_qid inside:
      * {{wikidata link|Qold ...}}
      * WD=Qold   or   qid=Qold   (inside any template, e.g. {{ill|...}})
    Returns (new_text, count).
    """
    count = 0

    pat_wdlink = re.compile(
        r"(\{\{\s*wikidata\s*link\s*\|\s*)" + re.escape(old_qid) + r"(\b)",
        re.IGNORECASE,
    )
    new_text, n = pat_wdlink.subn(lambda m: m.group(1) + new_qid + m.group(2), text)
    count += n

    pat_kv = re.compile(
        r"(\b(?:WD|qid)\s*=\s*)" + re.escape(old_qid) + r"(\b)",
        re.IGNORECASE,
    )
    new_text, n = pat_kv.subn(lambda m: m.group(1) + new_qid + m.group(2), new_text)
    count += n

    return new_text, count


def parse_qs_text(text):
    """Yield (qid, page_title) from the body of the on-wiki QS page."""
    for raw in text.splitlines():
        m = QS_LINE_RE.match(raw)
        if m:
            yield m.group(1), m.group(2).strip()


# ─── MAIN ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Cap on pages edited per run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Run tag appended to the edit summary for auditing.")
    parser.add_argument("--local", action="store_true",
                        help="Ignore WIKI_USERNAME/WIKI_PASSWORD env vars and "
                             "prompt for credentials interactively (for local runs).")
    parser.add_argument("--input", "-i",
                        help="Read QS lines from this file instead of from the "
                             "live [[QuickStatements/P11250]] page. Useful for "
                             "local runs against a specific list.")
    args = parser.parse_args()

    if args.local:
        username = input("shintowiki username: ").strip()
        if not username:
            print("No username entered; aborting.")
            sys.exit(1)
        password = getpass.getpass(f"Password for {username}: ")
        if not password:
            print("No password entered; aborting.")
            sys.exit(1)
    else:
        username = USERNAME
        password = PASSWORD
        if not password:
            print("WIKI_PASSWORD env var is empty. Either set it, or pass --local "
                  "to enter credentials interactively.")
            sys.exit(1)

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=ua_for(WIKI_URL))
    site.connection.timeout = 120
    login_with_retry(site, username, password)
    print(f"Logged in as {username}")

    # Get QS lines from either --input file or live wiki page
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            qs_text = f.read()
        source_label = args.input
    else:
        qs_page = site.pages[QS_PAGE_TITLE]
        qs_text = qs_page.text()
        source_label = f"[[{QS_PAGE_TITLE}]]"
    if not qs_text:
        print(f"{source_label} is empty; nothing to check.")
        return

    entries = list(parse_qs_text(qs_text))
    # Unique (qid, page)
    seen = set()
    unique = []
    for qid, title in entries:
        key = (qid, title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    print(f"Parsed {len(unique)} unique (QID, page) pairs from {source_label}.")

    qids = sorted({q for q, _ in unique})
    print(f"Checking {len(qids)} QIDs against Wikidata for merges…")
    redirects = resolve_redirects(qids)
    if not redirects:
        print("No merged QIDs found.")
        return
    print(f"Found {len(redirects)} merged QID(s):")
    for old, new in sorted(redirects.items()):
        print(f"  {old} → {new}")

    to_fix = [(q, t) for q, t in unique if q in redirects]
    print(f"{len(to_fix)} page reference(s) potentially need rewriting.\n")

    edits = 0
    skipped_no_match = 0

    for old_qid, title in to_fix:
        if edits >= args.max_edits:
            print(f"Hit --max-edits ({args.max_edits}); stopping.")
            break

        new_qid = redirects[old_qid]
        print(f"[[{title}]]  {old_qid} → {new_qid}")
        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            print(f"  ERROR reading page: {e}")
            continue

        if not text:
            print("  (page empty or missing; skip)")
            continue

        new_text, count = rewrite_qid(text, old_qid, new_qid)
        if count == 0:
            print(f"  (no references to {old_qid} found in wikitext; skip)")
            skipped_no_match += 1
            continue

        print(f"  {count} reference(s) rewritten")
        if not args.apply:
            print("  [DRY] would save")
            continue

        try:
            summary = f"Bot: fix merged QID {old_qid} → {new_qid} {args.run_tag}"
            page.save(new_text, summary=summary)
            edits += 1
            print(f"  SAVED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"  SAVE FAILED: {e}")

    print(f"\n{'=' * 50}")
    print(f"Pages edited:              {edits}")
    print(f"Pages with no QID match:   {skipped_no_match}")
    print(f"Merged QIDs found:         {len(redirects)}")


if __name__ == "__main__":
    main()
