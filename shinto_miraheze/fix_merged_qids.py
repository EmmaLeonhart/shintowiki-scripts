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

Runs in CI on the EmmaBot schedule — uses the standard
``WIKI_USERNAME`` / ``WIKI_PASSWORD`` environment variables. Standard
``--apply``, ``--max-edits``, ``--run-tag`` flags. Default is dry-run.

To run locally under your own account, pass ``--local``. That ignores the
env vars and prompts for username + password on the console. Example:

    python shinto_miraheze/fix_merged_qids.py --local --apply \
        --max-edits 20 --run-tag "[local]"
"""

import argparse
import getpass
import io
import os
import re
import sys
import time

import mwclient
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

QS_PAGE_TITLE = "QuickStatements/P11250"

USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WD_API = "https://www.wikidata.org/w/api.php"

QS_LINE_RE = re.compile(r'^\s*(Q\d+)\s*\|\s*P\d+\s*\|\s*"shinto:(.+?)"\s*$')
QID_RE = re.compile(r'^Q\d+$')


# ─── WIKIDATA REDIRECT LOOKUP ──────────────────────────────

def resolve_redirects(qids):
    """
    Ask Wikidata which QIDs redirect elsewhere. Returns dict
    {old_qid: new_qid} for QIDs that are merged. Bail on 429 per policy.
    """
    mapping = {}
    qids = list(qids)
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        try:
            resp = requests.get(
                WD_API,
                params={
                    "action": "query",
                    "titles": "|".join(batch),
                    "redirects": 1,
                    "format": "json",
                    "formatversion": "2",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            if resp.status_code == 429:
                print("  [bail] HTTP 429 from Wikidata; stopping.")
                sys.exit(0)
            resp.raise_for_status()
            data = resp.json().get("query", {})
            for r in data.get("redirects", []) or []:
                src = r.get("from")
                dst = r.get("to")
                if src and dst and QID_RE.match(src) and QID_RE.match(dst):
                    mapping[src] = dst
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [warn] Wikidata query failed for batch starting {batch[0]}: {e}")
        time.sleep(0.4)
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

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(username, password)
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
