#!/usr/bin/env python3
"""
sync_miraheze_unique_pages.py
==============================
Bidirectional sync between [[Category:Independently git synced pages]] on
shinto.miraheze.org and the local ``miraheze_unique/`` directory.

This is the miraheze half of the per-wiki independently-synced pattern.
Pages in this category are intentionally divergent from their fandom-side
counterparts (Lua, ``{{q}}``, ``d:`` interwiki, etc. work on miraheze but
not on fandom). The fandom-side counterpart lives in ``fandom_unique/``
and is synced by ``sync_fandom_unique_pages.py`` against shinto.fandom.com.
The two wikis never write to each other; the git repo is the hub.

Patterned on ``sync_git_synced_pages.py``. The conflict policy is the
same (repo wins on simultaneous-change). Discovery is by category on
miraheze; the script also picks up local files whose title is missing
from the wiki category and pushes them, treating the repo as the
source of truth for membership.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import mwclient
from wiki_login import login_with_retry

# Put the repo root on sys.path so the shinto_miraheze namespace
# resolves. No __init__.py in shinto_miraheze/, so the script
# directory alone isn't enough.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shinto_miraheze.sync_revision_aware import head_commit, resolve_conflict
from shinto_miraheze.title_filename import (  # noqa: E402
    assign_filenames, filename_to_title, title_to_filename,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

CATEGORY = "Independently git synced pages"
CATEGORY_NAMESPACES = "0|10|14"  # main, Template, Category

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WIKI_DIR = REPO_ROOT / "miraheze_unique"
STATE_FILE = SCRIPT_DIR / "sync_miraheze_unique_pages.state"



CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Independently git synced pages\s*\]\]',
    re.IGNORECASE,
)






def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_state(path: Path) -> dict:
    # STATE FILES REMOVED 2026-05-30 — see sync_git_synced_pages.load_state for the
    # rationale. Always {} → baselines None → differing pages resolve by
    # most-recent-edit timestamp; equal pages no-op; orphan/delete keys off the
    # category tag, not the baseline.
    return {}


def save_state(path: Path, state: dict) -> None:
    # No-op: state is no longer persisted (see load_state).
    return


def iter_category_with_revisions(site, category_name, namespaces):
    """Yield (title, revid, text) for every page currently in the category.

    Two-pass implementation. The naive single-pass version (generator +
    prop=revisions + rvprop=content) silently drops pages: MediaWiki
    caps the number of pages returned WITH content per response (~50),
    and continuation continues the *revisions* fetch on the same page
    set rather than serving the next slice cleanly. Pages missed by
    that cap look like they fell out of the category, triggering this
    script's orphan-PUSH path and overwriting genuine wiki edits with
    stale local content. Ported from sync_git_synced_pages.py — see
    that file's identical helper for the original fix."""
    titles: list[str] = []
    p1 = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category_name}",
        "cmnamespace": namespaces,
        "cmlimit": "max",
        "cmprop": "title",
        "formatversion": "2",
    }
    while True:
        result = site.api("query", **p1)
        for m in result.get("query", {}).get("categorymembers", []) or []:
            t = m.get("title")
            if t:
                titles.append(t)
        if "continue" in result:
            p1.update(result["continue"])
        else:
            break

    seen: set[str] = set()
    unique_titles: list[str] = []
    for t in titles:
        if t in seen:
            continue
        seen.add(t)
        unique_titles.append(t)

    BATCH = 50
    for i in range(0, len(unique_titles), BATCH):
        batch = unique_titles[i:i + BATCH]
        p2 = {
            "titles": "|".join(batch),
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvslots": "main",
            "formatversion": "2",
        }
        seen_in_batch: set[str] = set()
        while True:
            result = site.api("query", **p2)
            for page in result.get("query", {}).get("pages", []) or []:
                if page.get("missing"):
                    continue
                title = page.get("title")
                if not title or title in seen_in_batch:
                    continue
                revs = page.get("revisions") or []
                if not revs:
                    continue
                rev = revs[0]
                revid = rev.get("revid")
                text = rev.get("slots", {}).get("main", {}).get("content", "")
                if revid is None:
                    continue
                seen_in_batch.add(title)
                yield title, revid, text
            if "continue" in result:
                p2.update(result["continue"])
            else:
                break


def fetch_page(site, title):
    """Return (exists, revid, text) for a single page on `site`."""
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
    return True, rev.get("revid"), rev.get("slots", {}).get("main", {}).get("content", "")


def _fetch_latest_revid(site, title):
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return None
    revs = pages[0].get("revisions") or []
    if not revs:
        return None
    return revs[0].get("revid")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually push/pull edits (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max wiki edits per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL} as {USERNAME}")

    current_head = head_commit(REPO_ROOT)  # stamped onto every state entry
    print(f"Current HEAD: {current_head}")

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state(STATE_FILE)
    print(f"State: {len(state)} tracked pages")

    print(f"Fetching [[Category:{CATEGORY}]] members with content ...")
    wiki_pages = {}
    for title, revid, text in iter_category_with_revisions(
            site, CATEGORY, CATEGORY_NAMESPACES):
        wiki_pages[title] = (revid, text)
    print(f"Wiki:  {len(wiki_pages)} pages in category")

    # Filenames are assigned for the WHOLE title set at once, not per title.
    # Two wiki titles differing only in case (Template:Infobox Historic Site vs
    # ...historic site) map to one filename on a case-insensitive filesystem,
    # which jams the checkout and deadlocks git pull --rebase. assign_filenames
    # case-escapes only within a colliding group, so every other page keeps the
    # filename it has always had. See shinto_miraheze/title_filename.py.
    filenames = assign_filenames(wiki_pages.keys())

    local_files = {}
    for p in WIKI_DIR.iterdir():
        if p.is_file() and p.suffix == ".wiki":
            local_files[filename_to_title(p.name)] = p
    print(f"Local: {len(local_files)} .wiki files\n")

    pulled = pushed = pushed_new = skipped = conflicts = errors = 0
    edits_performed = 0

    # Pass 1: pages currently in the wiki category.
    for title, (wiki_revid, wiki_text) in wiki_pages.items():
        local_path = WIKI_DIR / filenames[title]
        entry = state.get(title) or {}
        base_revid = entry.get("revid")
        base_sha = entry.get("sha")
        base_commit = entry.get("sync_commit")
        wiki_sha = sha1_text(wiki_text)

        if not local_path.exists():
            if not args.apply:
                print(f"[DRY] PULL new: {title}")
                pulled += 1
                continue
            try:
                local_path.write_text(wiki_text, encoding="utf-8", newline="\n")
                state[title] = {"revid": wiki_revid, "sha": wiki_sha, "sync_commit": current_head}
                pulled += 1
                print(f"PULL  {title}  (rev {wiki_revid})")
            except Exception as e:
                errors += 1
                print(f"ERROR writing {title}: {e}")
            continue

        try:
            local_text = local_path.read_text(encoding="utf-8")
        except Exception as e:
            errors += 1
            print(f"ERROR reading {title}: {e}")
            continue
        local_sha = sha1_text(local_text)

        if local_sha == wiki_sha:
            if base_revid != wiki_revid or base_sha != wiki_sha or base_commit != current_head:
                state[title] = {"revid": wiki_revid, "sha": wiki_sha, "sync_commit": current_head}
            continue

        wiki_changed = base_revid != wiki_revid
        local_changed = base_sha is None or local_sha != base_sha

        if wiki_changed and not local_changed:
            if not args.apply:
                print(f"[DRY] PULL updated: {title}  ({base_revid} -> {wiki_revid})")
                pulled += 1
                continue
            try:
                local_path.write_text(wiki_text, encoding="utf-8", newline="\n")
                state[title] = {"revid": wiki_revid, "sha": wiki_sha, "sync_commit": current_head}
                pulled += 1
                print(f"PULL  {title}  ({base_revid} -> {wiki_revid})")
            except Exception as e:
                errors += 1
                print(f"ERROR writing {title}: {e}")
            continue

        if local_changed and not wiki_changed:
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PUSH: {title}")
                pushed += 1
                continue
            try:
                page = site.pages[title]
                result = page.save(
                    local_text,
                    summary=f"Sync from repo miraheze_unique/ {args.run_tag}",
                )
                new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
                state[title] = {"revid": new_revid, "sha": local_sha, "sync_commit": current_head}
                pushed += 1
                edits_performed += 1
                print(f"PUSH  {title}  (new rev {new_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR saving {title}: {e}")
            continue

        # Both sides changed. Revision-aware: whichever side has more revs
        # since baseline wins. Tie / missing-baseline falls back to the
        # static "repo wins" policy for this directory.
        conflicts += 1
        rel_path = str(local_path.relative_to(REPO_ROOT)).replace(os.sep, "/")
        winner = resolve_conflict(
            site=site, title=title,
            baseline_revid=base_revid, baseline_commit=base_commit,
            repo_root=REPO_ROOT, rel_file_path=rel_path,
            static_policy="repo",
        )

        if winner == "wiki":
            if not args.apply:
                print(f"[DRY] PULL (conflict, wiki has more revs): {title}  ({base_revid} -> {wiki_revid})")
                pulled += 1
                continue
            try:
                local_path.write_text(wiki_text, encoding="utf-8", newline="\n")
                state[title] = {"revid": wiki_revid, "sha": wiki_sha, "sync_commit": current_head}
                pulled += 1
                print(f"PULL  {title}  (conflict, wiki wins on revision count; {base_revid} -> {wiki_revid})")
            except Exception as e:
                errors += 1
                print(f"ERROR writing {title}: {e}")
            continue

        # winner == "repo" — push as before.
        if edits_performed >= args.max_edits:
            skipped += 1
            print(f"CONFLICT (repo wins): {title}  (wiki {base_revid} -> {wiki_revid}) - deferred, edit limit reached")
            continue
        if not args.apply:
            print(f"[DRY] PUSH (conflict, repo wins): {title}")
            pushed += 1
            continue
        try:
            page = site.pages[title]
            result = page.save(
                local_text,
                summary=f"Sync from repo miraheze_unique/ (overwriting divergent wiki edit; repo wins on revision count) {args.run_tag}",
            )
            new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
            state[title] = {"revid": new_revid, "sha": local_sha, "sync_commit": current_head}
            pushed += 1
            edits_performed += 1
            print(f"PUSH  {title}  (conflict, repo wins; wiki {base_revid} -> {wiki_revid} overwritten, new rev {new_revid})")
            time.sleep(THROTTLE)
        except Exception as e:
            errors += 1
            print(f"ERROR saving {title}: {e}")

    # Pass 2: local files not in the wiki category. Push if the file
    # carries the category tag (treat as new content), else delete the
    # local file (wiki is the source of truth for membership, matching
    # sync_git_synced_pages.py semantics).
    orphans = sorted(set(local_files) - set(wiki_pages))
    for title in orphans:
        local_path = local_files[title]
        try:
            local_text = local_path.read_text(encoding="utf-8")
        except Exception as e:
            errors += 1
            print(f"ERROR reading orphan {title}: {e}")
            continue

        cat_in_local = bool(CAT_RE.search(local_text))
        local_sha = sha1_text(local_text)

        if cat_in_local:
            # Repo wants this page in the category. Push local content;
            # creates the wiki page if missing or updates if existing
            # but uncategorised. The category tag is in the local
            # wikitext itself, so a successful push lands the page in
            # the category on miraheze too.
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PUSH (repo-only, has category): {title}")
                pushed_new += 1
                continue
            try:
                page = site.pages[title]
                result = page.save(
                    local_text,
                    summary=f"Sync from repo miraheze_unique/ (seeding into [[Category:{CATEGORY}]]) {args.run_tag}",
                )
                new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title)
                state[title] = {"revid": new_revid, "sha": local_sha, "sync_commit": current_head}
                pushed_new += 1
                edits_performed += 1
                print(f"PUSH-NEW  {title}  (new rev {new_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR pushing new {title}: {e}")
            continue

        # Local has no category tag and the wiki dropped it from the
        # category — delete the local file. Recoverable from git history.
        if not args.apply:
            print(f"[DRY] DELETE local (no category in either side): {title}")
            continue
        try:
            local_path.unlink()
            state.pop(title, None)
            print(f"DELETE  {title}  (no longer tracked)")
        except Exception as e:
            errors += 1
            print(f"ERROR deleting {title}: {e}")

    for title in list(state.keys()):
        if title not in wiki_pages and title not in local_files:
            state.pop(title, None)

    if args.apply:
        save_state(STATE_FILE, state)

    print(f"\n{'=' * 60}")
    print(f"Pulled (wiki -> repo):           {pulled}")
    print(f"Pushed (repo -> wiki, existing): {pushed}")
    print(f"Pushed (repo -> wiki, new):      {pushed_new}")
    print(f"Skipped (edit limit):            {skipped}")
    print(f"Conflicts (repo wins):           {conflicts}")
    print(f"Errors:                          {errors}")


if __name__ == "__main__":
    main()
