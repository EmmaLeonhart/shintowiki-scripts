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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shinto_miraheze.sync_revision_aware import (
    head_commit, resolve_conflict, LOWERCASE_COLLISION_TITLES,
)

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
            f"sync_fandom_unique_pages disabled: past FANDOM_SUNSET_DATE "
            f"({FANDOM_SUNSET_DATE.isoformat()}). No fandom reads or writes."
        )
        return 0

    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    site = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print(f"Logged in to {FAN_HOST} as {FANDOM_USERNAME}")

    current_head = head_commit(REPO_ROOT)  # stamped onto every state entry
    print(f"Current HEAD: {current_head}")

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
        if title in LOWERCASE_COLLISION_TITLES:
            # Case-collision lowercase twin being deleted on-wiki by
            # delete_lowercase_template_collisions.py. Skip entirely so we
            # never recreate it (the deleter would fight us) and never
            # decategorize the wiki page (keeps the deleter's byte-identity
            # gate intact). See LOWERCASE_COLLISION_TITLES.
            skipped += 1
            continue
        local_path = WIKI_DIR / title_to_filename(title)
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
                    summary=f"Sync from repo fandom_unique/ {args.run_tag}",
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

        # Both sides changed. Revision-aware: whichever has more revs
        # since baseline wins; tie/missing-baseline → static "repo" policy.
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
                summary=f"Sync from repo fandom_unique/ (overwriting divergent wiki edit; repo wins on revision count) {args.run_tag}",
            )
            new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
            state[title] = {"revid": new_revid, "sha": local_sha, "sync_commit": current_head}
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
        if title in LOWERCASE_COLLISION_TITLES:
            continue  # see LOWERCASE_COLLISION_TITLES — never recreate
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
                state[title] = {"revid": new_revid, "sha": local_sha, "sync_commit": current_head}
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
    # Per-page save failures (e.g. Fandom's Maps extension rejecting a save
    # because an <embedmap> on the page references a map that doesn't exist
    # — fandom-side data quality, not something we can fix from the bot)
    # are best-effort: surfaced in the printed summary, but they must not
    # fail the workflow. Otherwise a single broken remote page blocks the
    # entire daily sync indefinitely. Infrastructure-level failures (login
    # error, network outage) raise out unhandled and crash the script,
    # which is the right behavior. Mirrors the policy already used by
    # sync_miraheze_unique_pages.py.
    return 0


if __name__ == "__main__":
    sys.exit(main())
