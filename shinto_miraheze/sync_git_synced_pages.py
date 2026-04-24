#!/usr/bin/env python3
"""
sync_git_synced_pages.py
========================
Bidirectional sync between [[Category:Git synced pages]] on
shinto.miraheze.org and the local ``git_synced/`` directory.

Every page in the category is mirrored as ``<title>.wiki`` in
``git_synced/``. Changes on either side are detected by comparing:

  * wiki revid vs. last-synced revid          (wiki edits)
  * local content sha1 vs. last-synced sha1   (repo edits)

Resolution per page:
  * wiki changed, local unchanged  → pull wiki → local
  * local changed, wiki unchanged  → push local → wiki
  * both unchanged                 → no-op
  * both changed                   → push local → wiki (repo is the
                                     source of truth; any divergent
                                     wiki edit gets overwritten)

If a page is no longer in the category on the wiki, its local copy is
deleted — wiki is the source of truth for category membership. If the
category tag is missing from the local file, the edit is still pushed
(with the category removed on the wiki) and the local copy deleted,
mirroring how ``sync_need_translation.py`` handles an explicit opt-out.

Patterned after ``sync_need_translation.py`` — see that file's
conflict-detection logic as reference. Namespaces covered:
main (0), Template (10), Category (14), so that tagged templates and
category descriptions sync alongside mainspace content.

State lives in ``sync_git_synced_pages.state`` (JSON). Default mode is
dry-run; pass ``--apply`` to actually push/pull edits.
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

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

CATEGORY = "Git synced pages"
CATEGORY_NAMESPACES = "0|10|14"  # main, Template, Category

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WIKI_DIR = REPO_ROOT / "git_synced"
STATE_FILE = SCRIPT_DIR / "sync_git_synced_pages.state"

USER_AGENT = "GitSyncedPagesBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

_FORBIDDEN = set('<>:"/\\|?*')

CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Git synced pages\s*\]\]',
    re.IGNORECASE,
)


# ─── FILENAME MAPPING ──────────────────────────────────────
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


# ─── HELPERS ───────────────────────────────────────────────
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
    """Yield (title, revid, text) for every page currently in the category."""
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
        pages = result.get("query", {}).get("pages", [])
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
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return None
    revs = pages[0].get("revisions") or []
    if not revs:
        return None
    return revs[0].get("revid")


# ─── MAIN ──────────────────────────────────────────────────
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
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state(STATE_FILE)
    print(f"State: {len(state)} tracked pages")

    print(f"Fetching [[Category:{CATEGORY}]] members with content ...")
    wiki_pages = {}  # title -> (revid, text)
    for title, revid, text in iter_category_with_revisions(
            site, CATEGORY, CATEGORY_NAMESPACES):
        wiki_pages[title] = (revid, text)
    print(f"Wiki:  {len(wiki_pages)} pages in category")

    local_files = {}  # title -> Path
    for p in WIKI_DIR.iterdir():
        if p.is_file() and p.suffix == ".wiki":
            local_files[filename_to_title(p.name)] = p
    print(f"Local: {len(local_files)} .wiki files\n")

    pulled = pushed = deleted_local = skipped = conflicts = errors = 0
    edits_performed = 0

    # ── Pass 1: pages currently in the wiki category ──
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
                print(f"[DRY] PULL updated: {title}  ({base_revid} → {wiki_revid})")
                pulled += 1
                continue
            try:
                local_path.write_text(wiki_text, encoding="utf-8", newline="\n")
                state[title] = {"revid": wiki_revid, "sha": wiki_sha}
                pulled += 1
                print(f"PULL  {title}  ({base_revid} → {wiki_revid})")
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
                    summary=f"Sync from repo git_synced/ {args.run_tag}",
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

        # Both sides changed since the last sync. Policy: repo is the
        # source of truth — push local → wiki, overwriting the wiki's
        # divergent edit. Track it as a conflict counter for visibility,
        # but don't skip.
        conflicts += 1
        if edits_performed >= args.max_edits:
            skipped += 1
            print(f"CONFLICT (repo wins): {title}  (wiki {base_revid} → {wiki_revid}) — deferred, edit limit reached")
            continue
        if not args.apply:
            print(f"[DRY] PUSH (conflict → repo wins): {title}  (wiki {base_revid} → {wiki_revid})")
            pushed += 1
            continue
        try:
            page = site.pages[title]
            result = page.save(
                local_text,
                summary=f"Sync from repo git_synced/ (overwriting divergent wiki edit; repo is source of truth) {args.run_tag}",
            )
            new_revid = (result or {}).get("newrevid") or _fetch_latest_revid(site, title) or wiki_revid
            state[title] = {"revid": new_revid, "sha": local_sha}
            pushed += 1
            edits_performed += 1
            print(f"PUSH  {title}  (conflict → repo wins; wiki {base_revid} → {wiki_revid} overwritten, new rev {new_revid})")
            time.sleep(THROTTLE)
        except Exception as e:
            errors += 1
            print(f"ERROR saving {title}: {e}")

    # ── Pass 2: local files whose title is no longer in the wiki category ──
    orphans = sorted(set(local_files) - set(wiki_pages))
    for title in orphans:
        local_path = local_files[title]
        try:
            local_text = local_path.read_text(encoding="utf-8")
        except Exception as e:
            errors += 1
            print(f"ERROR reading orphan {title}: {e}")
            continue

        cat_still_present = bool(CAT_RE.search(local_text))
        entry = state.get(title) or {}
        base_sha = entry.get("sha")
        local_sha = sha1_text(local_text)

        if not cat_still_present:
            # User removed the category in the repo → push & untrack.
            if edits_performed >= args.max_edits:
                skipped += 1
                continue
            if not args.apply:
                print(f"[DRY] PUSH+DELETE (cat removed locally): {title}")
                pushed += 1
                deleted_local += 1
                continue
            try:
                page = site.pages[title]
                if page.exists:
                    if base_sha is None or local_sha != base_sha:
                        page.save(
                            local_text,
                            summary=f"Sync from repo: removed from Git synced pages category {args.run_tag}",
                        )
                        edits_performed += 1
                        pushed += 1
                        time.sleep(THROTTLE)
                local_path.unlink()
                state.pop(title, None)
                deleted_local += 1
                print(f"PUSH+DELETE  {title}")
            except Exception as e:
                errors += 1
                print(f"ERROR pushing-then-deleting {title}: {e}")
            continue

        # Category still present in the repo, but wiki dropped the page
        # from the category — wiki is source of truth for membership.
        if base_sha is not None and local_sha != base_sha:
            print(f"WARN: {title} has uncommitted local edits but wiki dropped the category — deleting anyway (recoverable from git)")
        if not args.apply:
            print(f"[DRY] DELETE local (cat removed on wiki): {title}")
            deleted_local += 1
            continue
        try:
            local_path.unlink()
            state.pop(title, None)
            deleted_local += 1
            print(f"DELETE  {title}  (no longer in wiki category)")
        except Exception as e:
            errors += 1
            print(f"ERROR deleting {title}: {e}")

    for title in list(state.keys()):
        if title not in wiki_pages and title not in local_files:
            state.pop(title, None)

    if args.apply:
        save_state(STATE_FILE, state)

    print(f"\n{'=' * 60}")
    print(f"Pulled (wiki → repo):  {pulled}")
    print(f"Pushed (repo → wiki):  {pushed}")
    print(f"Deleted local files:   {deleted_local}")
    print(f"Skipped (edit limit):  {skipped}")
    print(f"Conflicts:             {conflicts}")
    print(f"Errors:                {errors}")


if __name__ == "__main__":
    main()
