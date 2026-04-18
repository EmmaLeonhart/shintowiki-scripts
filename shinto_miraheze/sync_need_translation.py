#!/usr/bin/env python3
"""
sync_need_translation.py
========================
Bidirectional sync between [[Category:Need translation]] on
shinto.miraheze.org and the local ``need_translation/`` directory.

For every page in the category a ``<title>.wiki`` file is kept with the
raw wikitext. Changes on either side are detected by comparing:

* wiki revid vs. last-synced revid           (detects wiki edits)
* local content sha1 vs. last-synced sha1    (detects repo edits)

Resolution per page:
  * wiki changed, local unchanged  → pull wiki → local
  * local changed, wiki unchanged  → push local → wiki
  * both unchanged                 → no-op
  * both changed                   → conflict, logged and skipped

Special case: if a local ``.wiki`` file no longer contains
``[[Category:Need translation]]``, the content is pushed to the wiki
(removing the category there too) and the local file is then deleted.

State lives in ``sync_need_translation.state`` (JSON). Default mode is
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
THROTTLE = 1.5

CATEGORY = "Need translation"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WIKI_DIR = REPO_ROOT / "need_translation"
STATE_FILE = SCRIPT_DIR / "sync_need_translation.state"

USER_AGENT = "NeedTranslationSyncBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

# Windows-forbidden chars. '%' is escaped as well so the mapping is reversible.
_FORBIDDEN = set('<>:"/\\|?*')

CAT_RE = re.compile(r'\[\[\s*Category\s*:\s*Need translation\s*\]\]', re.IGNORECASE)


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


def iter_category_with_revisions(site, category_name):
    """Yield (title, revid, text) for every page currently in the category."""
    params = {
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category_name}",
        "gcmnamespace": "0",
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
    for title, revid, text in iter_category_with_revisions(site, CATEGORY):
        wiki_pages[title] = (revid, text)
    print(f"Wiki:  {len(wiki_pages)} pages in category")

    local_files = {}  # title -> Path
    for p in WIKI_DIR.iterdir():
        if p.is_file() and p.suffix == ".wiki":
            local_files[filename_to_title(p.name)] = p
    print(f"Local: {len(local_files)} .wiki files\n")

    pulled = pushed = deleted_local = skipped = conflicts = errors = 0
    edits_performed = 0

    # ── Pass 1: pages that are currently in the wiki category ──
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

        # Identical content on both sides — refresh state and move on.
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
                    summary=f"Sync from repo need_translation/ {args.run_tag}",
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

        # Both changed → conflict.
        conflicts += 1
        print(f"CONFLICT: {title}  (wiki {base_revid} → {wiki_revid}, local sha changed) — skipped")

    # ── Pass 2: local files whose title is no longer in the category ──
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
            # User removed the category in the repo → push & delete.
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
                    # Only push if the repo actually diverges from the wiki.
                    if base_sha is None or local_sha != base_sha:
                        page.save(
                            local_text,
                            summary=f"Sync from repo: removed from Need translation category {args.run_tag}",
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

        # Category still present in the repo, but the wiki no longer lists the
        # page in the category — someone removed it on-wiki directly. Drop the
        # local copy; wiki is the source of truth for category membership.
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

    # Drop state entries for titles that are now neither local nor in the cat.
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
