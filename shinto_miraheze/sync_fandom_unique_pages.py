#!/usr/bin/env python3
"""
sync_fandom_unique_pages.py
============================
Bidirectional sync between [[Category:Independently git synced pages]] on
shinto.fandom.com and the local ``fandom_unique/`` directory.

This is the fandom half of the per-wiki independently-synced pattern.
Pages here are the fandom-side counterparts of pages in
``miraheze_unique/`` — they hold the *fandom* version of templates and
pages whose miraheze and fandom forms differ (Lua/{{q}}/d: not
available on fandom, Portable Infoboxes used instead of Scribunto-driven
infoboxes, etc.).

The two wikis never write to each other; the git repo is the hub.

Patterned on ``sync_git_synced_pages.py``. Conflict policy: repo wins
on simultaneous-change.
"""

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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FAN_HOST = "shinto.fandom.com"
FAN_PATH = "/"
FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")
THROTTLE = 2.5

CATEGORY = "Independently git synced pages"
CATEGORY_NAMESPACES = "0|10|14|828"  # main, Template, Category, Module

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WIKI_DIR = REPO_ROOT / "fandom_unique"
STATE_FILE = SCRIPT_DIR / "sync_fandom_unique_pages.state"

USER_AGENT = "FandomUniquePagesBot/1.0 (User:EmmaBot; shinto.fandom.com)"

_FORBIDDEN = set('<>:"/\\|?*')

CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Independently git synced pages\s*\]\]',
    re.IGNORECASE,
)


def title_to_filename(title: str) -> str:
    out = []
    for c in title:
        if c in _FORBIDDEN or c == "%":
            out.append(f"%{ord(c):02X}")
        else:
            out.append(c)
    return "".join(out) + ".wiki"


def filename_to_title(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".wiki") else filename
    return urllib.parse.unquote(name)


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually push/pull edits (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=100,
                        help="Max wiki edits per run (default 100).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    site = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print(f"Logged in to {FAN_HOST} as {FANDOM_USERNAME}")

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state(STATE_FILE)
    print(f"State: {len(state)} tracked pages")

    print(f"Fetching [[Category:{CATEGORY}]] members with content from {FAN_HOST} ...")
    wiki_pages = {}
    for title, revid, text in iter_category_with_revisions(
            site, CATEGORY, CATEGORY_NAMESPACES):
        wiki_pages[title] = (revid, text)
    print(f"Wiki:  {len(wiki_pages)} pages in category")

    local_files = {}
    for p in WIKI_DIR.iterdir():
        if p.is_file() and p.suffix == ".wiki":
            local_files[filename_to_title(p.name)] = p
    print(f"Local: {len(local_files)} .wiki files\n")

    pulled = pushed = pushed_new = skipped = conflicts = errors = 0
    edits_performed = 0

    for title, (wiki_revid, wiki_text) in wiki_pages.items():
        local_path = WIKI_DIR / title_to_filename(title)
        entry = state.get(title) or {}
        base_revid = entry.get("revid")
        base_sha = entry.get("sha")
        wiki_sha = sha1_text(wiki_text)

        if not local_path.exists():
            if not args.apply:
                print(f"[DRY] PULL new: {title}")
                pulled += 1
                continue
            try:
                local_path.write_text(wiki_text, encoding="utf-8", newline="\n")
                state[title] = {"revid": wiki_revid, "sha": wiki_sha}
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
            if base_revid != wiki_revid or base_sha != wiki_sha:
                state[title] = {"revid": wiki_revid, "sha": wiki_sha}
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
                state[title] = {"revid": wiki_revid, "sha": wiki_sha}
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
                    summary=f"Sync from repo fandom_unique/ {args.run_tag}",
                )
                new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
                state[title] = {"revid": new_revid, "sha": local_sha}
                pushed += 1
                edits_performed += 1
                print(f"PUSH  {title}  (new rev {new_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR saving {title}: {e}")
            continue

        conflicts += 1
        if edits_performed >= args.max_edits:
            skipped += 1
            print(f"CONFLICT (repo wins): {title}  (wiki {base_revid} -> {wiki_revid}) - deferred")
            continue
        if not args.apply:
            print(f"[DRY] PUSH (conflict, repo wins): {title}")
            pushed += 1
            continue
        try:
            page = site.pages[title]
            result = page.save(
                local_text,
                summary=f"Sync from repo fandom_unique/ (overwriting divergent wiki edit; repo is source of truth) {args.run_tag}",
            )
            new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
            state[title] = {"revid": new_revid, "sha": local_sha}
            pushed += 1
            edits_performed += 1
            print(f"PUSH  {title}  (conflict, repo wins; new rev {new_revid})")
            time.sleep(THROTTLE)
        except Exception as e:
            errors += 1
            print(f"ERROR saving {title}: {e}")

    # Pass 2: local files whose title is missing from fandom's category.
    # Either fandom doesn't have the page yet (need to create it) or the
    # category tag is missing from the wiki side. In both cases, push
    # local content if it carries the category tag.
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
                    summary=f"Sync from repo fandom_unique/ (seeding into [[Category:{CATEGORY}]]) {args.run_tag}",
                )
                new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title)
                state[title] = {"revid": new_revid, "sha": local_sha}
                pushed_new += 1
                edits_performed += 1
                print(f"PUSH-NEW  {title}  (new rev {new_revid})")
                time.sleep(THROTTLE)
            except Exception as e:
                errors += 1
                print(f"ERROR pushing new {title}: {e}")
            continue

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
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
