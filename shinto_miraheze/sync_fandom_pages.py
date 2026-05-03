#!/usr/bin/env python3
"""
sync_fandom_pages.py
====================
Bidirectional sync between [[Category:Fandom sync]] on shinto.miraheze.org
and the same-titled pages on shinto.fandom.com. Discovery is one-way:
the category lives on miraheze, so newly-tagged pages on miraheze enter
the sync set; once tagged, the page content is kept in step on BOTH
wikis.

Why bidirectional matters here: the pages in this category are
typically templates that interact with Lua / Scribunto. Lua doesn't run
on fandom, so the fandom version may need hand-edits to remain working
after a miraheze-side change — and conversely, fandom-side fixes to
the wikitext-only shim should propagate back so the miraheze copy
matches. Without bidirectional sync, edits on either wiki would silently
diverge.

Patterned after ``sync_git_synced_pages.py``; the only structural
difference is that the "other side" of the sync is shinto.fandom.com
rather than the local ``git_synced/`` directory. State per page is
``{mira_revid, mira_sha, fan_revid, fan_sha}`` so we can tell which
side changed since the last sync.

Conflict resolution: if BOTH wikis have changed since the last sync,
miraheze wins — its content is pushed to fandom, and the divergent
fandom edit is overwritten. The category and Lua content live on
miraheze, so it is the natural source of truth. Conflicts are counted
and logged so they're visible in the run summary.

Tolerance: if [[Category:Fandom sync]] does not yet exist on miraheze
the script logs that and exits with no work — the category is
intentionally a redlink until the first page is tagged into it.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# --- CONFIG -------------------------------------------------------------
MIRA_HOST = "shinto.miraheze.org"
MIRA_PATH = "/w/"
FAN_HOST = "shinto.fandom.com"
FAN_PATH = "/"
THROTTLE = 2.5

WIKI_USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
WIKI_PASSWORD = os.getenv("WIKI_PASSWORD", "")
FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")

CATEGORY = "Fandom sync"
CATEGORY_NAMESPACES = "0|10|14|828"  # main, Template, Category, Module

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "sync_fandom_pages.state"

USER_AGENT = (
    "FandomSyncBot/1.0 (User:EmmaBot; shinto.miraheze.org <-> shinto.fandom.com)"
)


# --- HELPERS ------------------------------------------------------------
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


def iter_category_with_revisions(site, category_name, namespaces):
    """Yield (title, revid, text) for every page currently in the category.

    Returns no results (silently) if the category page itself does not
    exist — the API just returns an empty member list, which we treat
    as "nothing to sync yet", not an error.
    """
    params = {
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category_name}",
        "gcmnamespace": namespaces,
        "gcmlimit": "max",
        "prop": "revisions",
        "rvprop": "ids|content",
        "rvslots": "main",
        "formatversion": "2",
    }
    while True:
        result = site.api("query", **params)
        pages = result.get("query", {}).get("pages", []) or []
        for page in pages:
            if page.get("missing"):
                continue
            revs = page.get("revisions") or []
            if not revs:
                continue
            rev = revs[0]
            revid = rev.get("revid")
            text = rev.get("slots", {}).get("main", {}).get("content", "")
            if revid is None:
                continue
            yield page["title"], revid, text
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def fetch_page(site, title: str):
    """Return (exists, revid, text) for a single page on `site`.

    `exists=False` means the page is missing on this wiki. revid/text
    are None in that case.
    """
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids|content",
        rvslots="main",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return False, None, None
    page = pages[0]
    if page.get("missing"):
        return False, None, None
    revs = page.get("revisions") or []
    if not revs:
        return False, None, None
    rev = revs[0]
    revid = rev.get("revid")
    text = rev.get("slots", {}).get("main", {}).get("content", "")
    return True, revid, text


def _fetch_latest_revid(site, title):
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return None
    revs = pages[0].get("revisions") or []
    if not revs:
        return None
    return revs[0].get("revid")


def write_page(site, title: str, text: str, summary: str) -> int | None:
    """Save `text` to `title` on `site`. Returns the new revid if known."""
    page = site.pages[title]
    result = page.save(text, summary=summary)
    new_revid = (result or {}).get("newrevid")
    if new_revid is None:
        new_revid = _fetch_latest_revid(site, title)
    return new_revid


# --- MAIN ---------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually push edits (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Max combined wiki edits per run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    print(f"Logging in to {MIRA_HOST}...")
    mira = mwclient.Site(MIRA_HOST, path=MIRA_PATH, clients_useragent=USER_AGENT)
    mira.connection.timeout = 120
    mira.login(WIKI_USERNAME, WIKI_PASSWORD)
    print(f"  OK as {WIKI_USERNAME}")

    print(f"Logging in to {FAN_HOST}...")
    fan = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    fan.connection.timeout = 120
    fan.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print(f"  OK as {FANDOM_USERNAME}")

    state = load_state(STATE_FILE)
    print(f"State: {len(state)} tracked pages")

    print(f"Fetching [[Category:{CATEGORY}]] members from {MIRA_HOST} ...")
    mira_pages = {}  # title -> (revid, text)
    for title, revid, text in iter_category_with_revisions(
            mira, CATEGORY, CATEGORY_NAMESPACES):
        mira_pages[title] = (revid, text)
    print(f"Miraheze: {len(mira_pages)} pages currently tagged")

    if not mira_pages:
        # The category may not exist yet (redlink), or no pages have been
        # tagged. Either way: nothing to sync. Untrack any stale state
        # entries (pages previously tagged but no longer in the category).
        if state:
            for title in list(state.keys()):
                state.pop(title, None)
            if args.apply:
                save_state(STATE_FILE, state)
            print("Untracked all stale state entries (category empty).")
        print("Nothing to do.")
        return 0

    pushed_to_fan = pulled_to_mira = pushed_new_to_fan = skipped = 0
    conflicts = errors = 0
    edits_performed = 0

    for title, (mira_revid, mira_text) in mira_pages.items():
        entry = state.get(title) or {}
        base_mira_revid = entry.get("mira_revid")
        base_mira_sha = entry.get("mira_sha")
        base_fan_revid = entry.get("fan_revid")
        base_fan_sha = entry.get("fan_sha")
        mira_sha = sha1_text(mira_text)

        try:
            fan_exists, fan_revid, fan_text = fetch_page(fan, title)
        except Exception as e:
            errors += 1
            print(f"ERROR fetching {title} from fandom: {e}")
            continue

        if not fan_exists:
            # Page exists on miraheze (it's in the category) but not on
            # fandom — push the miraheze content over to seed it.
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PUSH new -> fandom: {title}")
                pushed_new_to_fan += 1
                continue
            try:
                new_fan_revid = write_page(
                    fan, title, mira_text,
                    summary=f"Initial sync from {MIRA_HOST} {args.run_tag}",
                )
                state[title] = {
                    "mira_revid": mira_revid,
                    "mira_sha": mira_sha,
                    "fan_revid": new_fan_revid,
                    "fan_sha": mira_sha,
                }
                pushed_new_to_fan += 1
                edits_performed += 1
                print(f"PUSH-NEW  {title}  -> fandom rev {new_fan_revid}")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR creating {title} on fandom: {e}")
            continue

        fan_sha = sha1_text(fan_text)

        if mira_sha == fan_sha:
            # Already in sync. Refresh the state baseline if either
            # revid has moved (e.g. null edit, history merge) so future
            # change detection doesn't false-alarm.
            if (base_mira_revid != mira_revid
                    or base_fan_revid != fan_revid
                    or base_mira_sha != mira_sha
                    or base_fan_sha != fan_sha):
                state[title] = {
                    "mira_revid": mira_revid,
                    "mira_sha": mira_sha,
                    "fan_revid": fan_revid,
                    "fan_sha": fan_sha,
                }
            continue

        mira_changed = base_mira_revid != mira_revid
        fan_changed = (base_fan_revid is None) or (base_fan_revid != fan_revid)

        # First-time encounter (no state baseline): treat the diff as
        # miraheze-changed if the base is missing, so miraheze wins on
        # the bootstrap. Operators can preload state for one-off
        # bootstrapping in the other direction if needed.
        if base_mira_revid is None and base_fan_revid is None:
            mira_changed = True
            fan_changed = False

        if mira_changed and not fan_changed:
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PUSH miraheze -> fandom: {title}")
                pushed_to_fan += 1
                continue
            try:
                new_fan_revid = write_page(
                    fan, title, mira_text,
                    summary=f"Sync from {MIRA_HOST} {args.run_tag}",
                )
                state[title] = {
                    "mira_revid": mira_revid,
                    "mira_sha": mira_sha,
                    "fan_revid": new_fan_revid,
                    "fan_sha": mira_sha,
                }
                pushed_to_fan += 1
                edits_performed += 1
                print(f"PUSH  {title}  miraheze -> fandom (new rev {new_fan_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR pushing {title} to fandom: {e}")
            continue

        if fan_changed and not mira_changed:
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PULL fandom -> miraheze: {title}")
                pulled_to_mira += 1
                continue
            try:
                new_mira_revid = write_page(
                    mira, title, fan_text,
                    summary=f"Sync from {FAN_HOST} {args.run_tag}",
                )
                state[title] = {
                    "mira_revid": new_mira_revid,
                    "mira_sha": fan_sha,
                    "fan_revid": fan_revid,
                    "fan_sha": fan_sha,
                }
                pulled_to_mira += 1
                edits_performed += 1
                print(f"PULL  {title}  fandom -> miraheze (new rev {new_mira_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR pulling {title} to miraheze: {e}")
            continue

        # Both sides changed since last sync — miraheze wins.
        conflicts += 1
        if edits_performed >= args.max_edits:
            skipped += 1
            print(f"CONFLICT (mira wins): {title} — deferred, edit limit reached")
            continue
        if not args.apply:
            print(f"[DRY] PUSH miraheze -> fandom (conflict): {title}")
            pushed_to_fan += 1
            continue
        try:
            new_fan_revid = write_page(
                fan, title, mira_text,
                summary=(
                    f"Sync from {MIRA_HOST} (overwriting divergent fandom "
                    f"edit; miraheze is source of truth) {args.run_tag}"
                ),
            )
            state[title] = {
                "mira_revid": mira_revid,
                "mira_sha": mira_sha,
                "fan_revid": new_fan_revid,
                "fan_sha": mira_sha,
            }
            pushed_to_fan += 1
            edits_performed += 1
            print(f"PUSH  {title}  miraheze -> fandom (CONFLICT, mira wins, new rev {new_fan_revid})")
            time.sleep(THROTTLE)
        except Exception as e:
            errors += 1
            print(f"ERROR resolving conflict on {title}: {e}")

    # Untrack pages no longer in the category. We don't delete on either
    # wiki — removing the category just means "stop syncing", consistent
    # with the bidirectional contract.
    for title in list(state.keys()):
        if title not in mira_pages:
            state.pop(title, None)

    if args.apply:
        save_state(STATE_FILE, state)

    print(f"\n{'=' * 60}")
    print(f"Pushed miraheze -> fandom (existing): {pushed_to_fan}")
    print(f"Pushed miraheze -> fandom (new):      {pushed_new_to_fan}")
    print(f"Pulled fandom   -> miraheze:          {pulled_to_mira}")
    print(f"Skipped (edit limit):                 {skipped}")
    print(f"Conflicts (mira wins):                {conflicts}")
    print(f"Errors:                               {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
