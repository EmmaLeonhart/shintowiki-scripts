#!/usr/bin/env python3
"""
tag_deleted_qids_in_ill.py
============================
Walks all mainspace pages and finds {{ill}} templates with WD= parameters
pointing to deleted (non-existent) Wikidata QIDs. Replaces the QID with
DELETED_QID and adds [[Category:Pages with deleted QID in ill template]].

* Stateful -- tracks processed pages in a .state file so it can resume
  across pipeline runs.
* Processes up to --max-edits pages per run (default 100).
* When all pages have been processed, the state file resets so the
  next run starts a fresh sweep.

Default mode is dry-run. Use --apply to actually edit.
"""

import argparse
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

STATE_FILE = os.path.join(os.path.dirname(__file__), "tag_deleted_qids_in_ill.state")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "deleted_qids_report.txt")
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
WD_API = "https://www.wikidata.org/w/api.php"

CATEGORY_TAG = "[[Category:Pages with deleted QID in ill template]]"

ILL_RE = re.compile(r'\{\{ill\|([^{}]*)\}\}', re.IGNORECASE)
QID_RE = re.compile(r'^Q\d+$')


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


# ─── QID CHECKING ──────────────────────────────────────────

_qid_exists_cache = {}


def check_qid_exists(qid):
    """Check if a QID exists on Wikidata. Returns True/False."""
    if qid in _qid_exists_cache:
        return _qid_exists_cache[qid]

    try:
        resp = requests.get(WD_API, params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "info",
            "format": "json",
        }, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        entities = data.get("entities", {})
        entity = entities.get(qid, {})
        # A deleted/missing QID has "missing" key
        exists = "missing" not in entity
        _qid_exists_cache[qid] = exists
        return exists
    except Exception:
        # On error, assume exists (don't make false edits)
        return True


def check_qids_batch(qids):
    """Check multiple QIDs at once (up to 50). Returns dict of qid -> exists."""
    results = {}
    uncached = [q for q in qids if q not in _qid_exists_cache]
    for q in qids:
        if q in _qid_exists_cache:
            results[q] = _qid_exists_cache[q]

    # Batch in groups of 50
    for i in range(0, len(uncached), 50):
        batch = uncached[i:i + 50]
        try:
            resp = requests.get(WD_API, params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "info",
                "format": "json",
            }, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
            for qid in batch:
                entity = entities.get(qid, {})
                exists = "missing" not in entity
                _qid_exists_cache[qid] = exists
                results[qid] = exists
        except Exception:
            # On error, assume all exist
            for qid in batch:
                results[qid] = True
        time.sleep(0.5)

    return results


# ─── PAGE PROCESSING ───────────────────────────────────────

def extract_qids_from_page(text):
    """Extract all WD= and qid= QID values from {{ill}} templates on a page."""
    qids = set()
    for match in ILL_RE.finditer(text):
        params = match.group(1).split("|")
        for p in params:
            p = p.strip()
            if p.upper().startswith("WD=") or p.lower().startswith("qid="):
                val = p.split("=", 1)[1].strip()
                if QID_RE.match(val):
                    qids.add(val)
    return qids


def has_wd_param(text):
    """Check if any {{ill}} template on the page uses the old WD= parameter."""
    for match in ILL_RE.finditer(text):
        params = match.group(1).split("|")
        for p in params:
            if p.strip().upper().startswith("WD="):
                return True
    return False


def fix_ill_templates(text, deleted_qids):
    """Fix {{ill}} templates: rename WD= to qid=, and mark deleted QIDs as DELETED_QID."""
    def replacer(match):
        inner = match.group(1)
        params = inner.split("|")
        changed = False
        for i, p in enumerate(params):
            ps = p.strip()
            if ps.upper().startswith("WD=") or ps.lower().startswith("qid="):
                val = ps.split("=", 1)[1].strip()
                if val in deleted_qids:
                    params[i] = "qid=DELETED_QID"
                    changed = True
                elif ps.upper().startswith("WD="):
                    # Rename WD= to qid= (keep the valid QID)
                    params[i] = f"qid={val}"
                    changed = True
        if not changed:
            return match.group(0)
        return "{{ill|" + "|".join(params) + "}}"

    return ILL_RE.sub(replacer, text)


# ─── MAIN ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tag pages with deleted QIDs in {{ill}} templates."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit pages (default is dry-run).")
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

    # Get all mainspace pages
    print("Fetching all mainspace pages...")
    all_pages = []
    for page in site.allpages(namespace=0):
        all_pages.append(page.name)
    print(f"Found {len(all_pages)} mainspace pages")

    # Filter out already-processed
    pending = [t for t in all_pages if t not in done]
    print(f"Pending: {len(pending)} pages")

    if not pending:
        print("All pages processed -- clearing state for next cycle.")
        clear_state(STATE_FILE)
        return

    batch = pending[:args.max_edits]
    print(f"Processing batch of {len(batch)} pages\n")

    edits = 0
    pages_with_deleted = 0
    total_deleted_qids = 0
    report_lines = []

    for idx, title in enumerate(batch, 1):
        print(f"{idx}/{len(batch)}  [[{title}]]", end="")

        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            print(f"  ERROR reading: {e}")
            append_state(STATE_FILE, title)
            continue

        # Extract QIDs from {{ill}} templates
        qids = extract_qids_from_page(text)
        page_has_wd = has_wd_param(text)
        if not qids and not page_has_wd:
            print("  (no ill QIDs)")
            append_state(STATE_FILE, title)
            continue

        # Check which QIDs exist
        deleted = set()
        if qids:
            existence = check_qids_batch(list(qids))
            deleted = {q for q, exists in existence.items() if not exists}

        if not deleted and not page_has_wd:
            print(f"  ({len(qids)} QIDs all valid, no WD= to rename)")
            append_state(STATE_FILE, title)
            time.sleep(0.3)
            continue

        if deleted:
            print(f"  FOUND {len(deleted)} deleted QID(s): {', '.join(sorted(deleted))}")
            pages_with_deleted += 1
            total_deleted_qids += len(deleted)
            for q in sorted(deleted):
                report_lines.append(f"{title}\t{q}")
        elif page_has_wd:
            print(f"  (renaming WD= to qid=)")

        # Fix ill templates: rename WD= to qid=, mark deleted as DELETED_QID
        new_text = fix_ill_templates(text, deleted)

        # Add category if deleted QIDs found and not already present
        if deleted and CATEGORY_TAG not in new_text:
            new_text = new_text.rstrip() + "\n" + CATEGORY_TAG + "\n"

        if new_text == text:
            print("    (no changes after replacement)")
            append_state(STATE_FILE, title)
            continue

        # Build summary
        parts = []
        if deleted:
            parts.append(f"mark {len(deleted)} deleted QID(s) as DELETED_QID")
        wd_renamed = has_wd_param(text)
        if wd_renamed:
            parts.append("rename WD= to qid=")
        summary_desc = ", ".join(parts)

        if args.apply:
            try:
                summary = f"Bot: {summary_desc} in ill templates {args.run_tag}"
                page.save(new_text, summary=summary)
                edits += 1
                print(f"    SAVED ({summary_desc})")
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"    SAVE FAILED: {e}")
        else:
            print(f"    DRY RUN ({summary_desc})")

        append_state(STATE_FILE, title)

    # Write report
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        for line in report_lines:
            f.write(line + "\n")

    print(f"\n{'=' * 50}")
    print(f"Pages processed:       {len(batch)}")
    print(f"Pages with deleted QIDs: {pages_with_deleted}")
    print(f"Total deleted QIDs:    {total_deleted_qids}")
    print(f"Edits made:            {edits}")
    print(f"Report appended to:    {REPORT_FILE}")


if __name__ == "__main__":
    main()
