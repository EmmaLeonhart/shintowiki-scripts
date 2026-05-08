#!/usr/bin/env python3
"""
propagate_independent_category.py
==================================
Preflight for the independent-pages-sync pipeline. Ensures
[[Category:Independently git synced pages]] is tagged on BOTH wikis for
any title that is in the category on either wiki, or has a local file
in ``miraheze_unique/`` or ``fandom_unique/``.

Without this preflight, the two sync scripts can disagree on which
titles to operate on:

* a title tagged on miraheze but not on fandom would be pulled into
  ``miraheze_unique/`` but never into ``fandom_unique/``;
* a title with a fandom_unique/ override file but no fandom-side
  category tag would never be discovered by the fandom sync;
* etc.

This script edits the wiki minimally — it only adds the category to
pages that already exist on each wiki and lack the tag. It does NOT
create pages or copy content between directories; that's the job of
the sync scripts and (for fandom_unique seeding from miraheze_unique)
``bootstrap_seed_fandom_unique_from_miraheze.py``.
"""

import argparse
import io
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CATEGORY = "Independently git synced pages"
CATEGORY_NAMESPACES = "0|10|14|828"

MIRA_HOST = "shinto.miraheze.org"
MIRA_PATH = "/w/"
FAN_HOST = "shinto.fandom.com"
FAN_PATH = "/"

THROTTLE = 2.5

WIKI_USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
WIKI_PASSWORD = os.getenv("WIKI_PASSWORD", "")
FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")

USER_AGENT = "IndependentCategoryPropagator/1.0 (User:EmmaBot)"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MIRAHEZE_DIR = REPO_ROOT / "miraheze_unique"
FANDOM_DIR = REPO_ROOT / "fandom_unique"

CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Independently git synced pages\s*\]\]',
    re.IGNORECASE,
)


def filename_to_title(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".wiki") else filename
    return urllib.parse.unquote(name)


def category_titles(site, category, namespaces):
    out = set()
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmnamespace": namespaces,
        "cmlimit": "max",
        "formatversion": "2",
    }
    while True:
        result = site.api("query", **params)
        for m in result.get("query", {}).get("categorymembers", []) or []:
            out.add(m["title"])
        if "continue" in result:
            params.update(result["continue"])
        else:
            break
    return out


def fetch_text(site, title):
    """Return (exists, revid, text) for `title`."""
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
    return True, rev.get("revid"), rev.get("slots", {}).get("main", {}).get("content", "") or ""


def add_category(text: str, category: str) -> str:
    """Append [[Category:<category>]] to wikitext, inside the trailing
    <noinclude> block if one exists, otherwise on its own line at the end.
    """
    tag = f"[[Category:{category}]]"
    if CAT_RE.search(text):
        return text  # already has it
    # Prefer to insert before a closing </noinclude> if present.
    m = re.search(r'</noinclude>\s*$', text)
    if m:
        return text[:m.start()] + tag + "\n" + text[m.start():]
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + tag + "\n"


def ensure_tagged(site, label, title, run_tag, apply, max_edits, edits_so_far):
    """Add the category to `title` on `site` if missing. Returns
    (edited: bool, error_msg: str|None)."""
    exists, revid, text = fetch_text(site, title)
    if not exists:
        return False, None  # page missing on this wiki — sync scripts will create it
    if CAT_RE.search(text or ""):
        return False, None
    if edits_so_far >= max_edits:
        print(f"  SKIP (edit limit): {label}: {title}")
        return False, None
    new_text = add_category(text or "", CATEGORY)
    if not apply:
        print(f"  [DRY] TAG  {label}: {title}")
        return True, None
    try:
        page = site.pages[title]
        page.save(
            new_text,
            summary=f"Bot: tag [[Category:{CATEGORY}]] on this {label} wiki to mirror tagging on the other {run_tag}",
        )
        print(f"  TAG  {label}: {title}  (rev was {revid})")
        time.sleep(THROTTLE)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Max wiki edits per run (default 50, combined across both wikis).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    print(f"Logging in to {MIRA_HOST} ...")
    mira = mwclient.Site(MIRA_HOST, path=MIRA_PATH, clients_useragent=USER_AGENT)
    mira.connection.timeout = 120
    mira.login(WIKI_USERNAME, WIKI_PASSWORD)
    print(f"  OK as {WIKI_USERNAME}")

    print(f"Logging in to {FAN_HOST} ...")
    fan = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    fan.connection.timeout = 120
    fan.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print(f"  OK as {FANDOM_USERNAME}")

    print(f"\nFetching [[Category:{CATEGORY}]] members from {MIRA_HOST} ...")
    mira_cat = category_titles(mira, CATEGORY, CATEGORY_NAMESPACES)
    print(f"  {len(mira_cat)} titles")

    print(f"Fetching [[Category:{CATEGORY}]] members from {FAN_HOST} ...")
    fan_cat = category_titles(fan, CATEGORY, CATEGORY_NAMESPACES)
    print(f"  {len(fan_cat)} titles")

    mira_local = set()
    if MIRAHEZE_DIR.exists():
        for p in MIRAHEZE_DIR.iterdir():
            if p.is_file() and p.suffix == ".wiki":
                mira_local.add(filename_to_title(p.name))
    print(f"Local miraheze_unique/: {len(mira_local)} files")

    fan_local = set()
    if FANDOM_DIR.exists():
        for p in FANDOM_DIR.iterdir():
            if p.is_file() and p.suffix == ".wiki":
                fan_local.add(filename_to_title(p.name))
    print(f"Local fandom_unique/:   {len(fan_local)} files")

    universe = mira_cat | fan_cat | mira_local | fan_local
    print(f"\nUniverse of titles to ensure tagged on both wikis: {len(universe)}\n")

    edits = errors = 0

    # Tag on miraheze if missing from miraheze category.
    print("--- Pass 1: ensure category on miraheze ---")
    for title in sorted(universe - mira_cat):
        edited, err = ensure_tagged(
            mira, "miraheze", title, args.run_tag, args.apply,
            args.max_edits, edits,
        )
        if err:
            errors += 1
            print(f"  ERROR tagging miraheze {title}: {err}")
        elif edited:
            edits += 1

    # Tag on fandom if missing from fandom category.
    print("\n--- Pass 2: ensure category on fandom ---")
    for title in sorted(universe - fan_cat):
        edited, err = ensure_tagged(
            fan, "fandom", title, args.run_tag, args.apply,
            args.max_edits, edits,
        )
        if err:
            errors += 1
            print(f"  ERROR tagging fandom {title}: {err}")
        elif edited:
            edits += 1

    print(f"\n{'=' * 60}")
    print(f"Edits performed: {edits}")
    print(f"Errors:          {errors}")
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
