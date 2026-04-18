#!/usr/bin/env python3
"""
sync_main_page.py
=================
Bidirectional sync between the wiki page ``Main Page`` on
shinto.miraheze.org and the single file ``Main Page.wiki`` in the
repository root.

Only this one page is in scope. Unlike the category-driven syncs,
there is no category lookup: the script fetches the wiki page by
title, compares against the local file, and resolves using the same
revid + sha1 scheme as ``sync_duplicated_content.py``.

Resolution:
  * wiki changed, local unchanged  → pull wiki → local
  * local changed, wiki unchanged  → push local → wiki
  * both unchanged                 → no-op
  * both changed                   → conflict, logged and skipped

State lives in ``sync_main_page.state`` (JSON). Default mode is
dry-run; pass ``--apply`` to push/pull.
"""

import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

PAGE_TITLE = "Main Page"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOCAL_PATH = REPO_ROOT / "Main Page.wiki"
STATE_FILE = SCRIPT_DIR / "sync_main_page.state"

USER_AGENT = "MainPageSyncBot/1.0 (User:EmmaBot; shinto.miraheze.org)"


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path: Path, state: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def fetch_wiki_page(site, title):
    """Return (revid, text) for the live page, or (None, None) if missing."""
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids|content",
        rvslots="main",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None, None
    revs = pages[0].get("revisions") or []
    if not revs:
        return None, None
    rev = revs[0]
    revid = rev.get("revid")
    text = rev.get("slots", {}).get("main", {}).get("content", "")
    return revid, text


def _fetch_latest_revid(site, title):
    revid, _ = fetch_wiki_page(site, title)
    return revid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually push/pull edits (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=1,
                        help="Max wiki edits per run (default 1 — this script "
                             "only ever touches one page).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    state = load_state(STATE_FILE)
    entry = state.get(PAGE_TITLE) or {}
    base_revid = entry.get("revid")
    base_sha = entry.get("sha")

    wiki_revid, wiki_text = fetch_wiki_page(site, PAGE_TITLE)
    if wiki_revid is None:
        print(f"ERROR: wiki page [[{PAGE_TITLE}]] is missing or empty; aborting.")
        sys.exit(1)
    wiki_sha = sha1_text(wiki_text)
    print(f"Wiki:  rev {wiki_revid}  sha {wiki_sha[:8]}")

    local_exists = LOCAL_PATH.exists()
    if local_exists:
        local_text = LOCAL_PATH.read_text(encoding="utf-8")
        local_sha = sha1_text(local_text)
        print(f"Local: sha {local_sha[:8]}  ({LOCAL_PATH})")
    else:
        local_text = None
        local_sha = None
        print(f"Local: (missing at {LOCAL_PATH})")

    # ── Case 1: local file missing → pull ──
    if not local_exists:
        if not args.apply:
            print(f"[DRY] PULL new: {PAGE_TITLE}")
            return
        LOCAL_PATH.write_text(wiki_text, encoding="utf-8", newline="\n")
        state[PAGE_TITLE] = {"revid": wiki_revid, "sha": wiki_sha}
        save_state(STATE_FILE, state)
        print(f"PULL  {PAGE_TITLE}  (rev {wiki_revid})")
        return

    # ── Case 2: identical on both sides ──
    if local_sha == wiki_sha:
        if base_revid != wiki_revid or base_sha != wiki_sha:
            state[PAGE_TITLE] = {"revid": wiki_revid, "sha": wiki_sha}
            if args.apply:
                save_state(STATE_FILE, state)
        print("NO-OP (content identical)")
        return

    wiki_changed = base_revid != wiki_revid
    local_changed = base_sha is None or local_sha != base_sha

    # ── Case 3: wiki edited, repo untouched → pull ──
    if wiki_changed and not local_changed:
        if not args.apply:
            print(f"[DRY] PULL updated: {PAGE_TITLE}  ({base_revid} → {wiki_revid})")
            return
        LOCAL_PATH.write_text(wiki_text, encoding="utf-8", newline="\n")
        state[PAGE_TITLE] = {"revid": wiki_revid, "sha": wiki_sha}
        save_state(STATE_FILE, state)
        print(f"PULL  {PAGE_TITLE}  ({base_revid} → {wiki_revid})")
        return

    # ── Case 4: repo edited, wiki untouched → push ──
    if local_changed and not wiki_changed:
        if not args.apply:
            print(f"[DRY] PUSH: {PAGE_TITLE}")
            return
        page = site.pages[PAGE_TITLE]
        result = page.save(
            local_text,
            summary=f"Sync from repo Main Page.wiki {args.run_tag}",
        )
        new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, PAGE_TITLE) or wiki_revid
        state[PAGE_TITLE] = {"revid": new_revid, "sha": local_sha}
        save_state(STATE_FILE, state)
        time.sleep(THROTTLE)
        print(f"PUSH  {PAGE_TITLE}  (new rev {new_revid})")
        return

    # ── Case 5: both sides changed since last sync → conflict ──
    print(f"CONFLICT: {PAGE_TITLE}  "
          f"(wiki {base_revid} → {wiki_revid}, local sha {base_sha[:8] if base_sha else '?'} → {local_sha[:8]}) "
          f"— skipped; resolve manually.")


if __name__ == "__main__":
    main()
