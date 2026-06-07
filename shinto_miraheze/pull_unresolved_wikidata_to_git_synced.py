#!/usr/bin/env python3
"""
pull_unresolved_wikidata_to_git_synced.py
=========================================
One-off / pre-orchestration puller for the "resolve interlanguage links via
local agentic RAG" operation (Emma, 2026-06-07).

The cohort: pages in [[Category:Pages without wikidata]] that ALREADY carry a
``{{wikidata link|...}}`` template but whose QID slot is empty (or that carry
the template at all without a resolved QID) — i.e. the pages the automatic
``wikidata_lookup`` resolver could NOT resolve by exact sitelink match. This
EXCLUDES the large legacy-literal-tag population (pages with no template at
all), which is being drained separately by the crud-category lifecycle.

What it does (read-only against the wiki; writes only local files):
  1. Walk Category:Pages without wikidata.
  2. Pull each member's current wikitext.
  3. Keep only members that contain a ``{{wikidata link`` template.
  4. Write each to ``git_synced/<title>.wiki`` (the bidirectional git<->miraheze
     sync dir), using the same title->filename convention as
     ``sync_git_synced_pages.py``.

This is PART 1 of the kickoff. After running it: commit + push (establishes the
files as locally-synced). PART 2 (a separate step) appends the git-sync
categories + an explanation and commits again, which the git-synced-sync
GitHub Action then propagates to the wiki. PART 3 is the per-page agentic
Wikidata resolution.

No --apply flag: it never edits the wiki, only the local working tree.
"""

import io
import os
import re
import sys
import time
import urllib.parse

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
USER_AGENT = "GitSyncedPagesBot/1.0 (User:EmmaBot; shinto.miraheze.org)"
CATEGORY = "Pages without wikidata"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GIT_SYNCED_DIR = os.path.join(REPO_ROOT, "git_synced")

# Matches a {{wikidata link}} template whether blank or with args.
WD_TEMPLATE_PRESENT_RE = re.compile(r"\{\{\s*wikidata\s*link\s*[|}]", re.IGNORECASE)

# Same forbidden-char set + encoding as sync_git_synced_pages.title_to_filename.
_FORBIDDEN = set('<>:"/\\|?*')


def title_to_filename(title: str) -> str:
    out = []
    for c in title:
        if c in _FORBIDDEN or c == "%":
            out.append(f"%{ord(c):02X}")
        else:
            out.append(c)
    return "".join(out) + ".wiki"


def fetch_cohort(session):
    """Yield (title, wikitext) for every Category:Pages without wikidata member
    that contains a {{wikidata link}} template."""
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{CATEGORY}",
        "gcmtype": "page",
        "gcmlimit": "50",
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
    }
    cont = {}
    while True:
        p = dict(params)
        p.update(cont)
        r = session.get(WIKI_API, params=p, timeout=60)
        if r.status_code == 429:
            print("HTTP 429 from wiki — bailing (no retries).")
            sys.exit(1)
        r.raise_for_status()
        data = r.json()
        for pg in data.get("query", {}).get("pages", []):
            try:
                txt = pg["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                continue
            if WD_TEMPLATE_PRESENT_RE.search(txt):
                yield pg["title"], txt
        if "continue" not in data:
            break
        cont = data["continue"]
        time.sleep(0.3)


def main():
    os.makedirs(GIT_SYNCED_DIR, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    written = skipped_existing = 0
    titles = []
    for title, wikitext in fetch_cohort(session):
        titles.append(title)
        path = os.path.join(GIT_SYNCED_DIR, title_to_filename(title))
        if os.path.exists(path):
            # Already a git_synced page — don't clobber the local copy.
            skipped_existing += 1
            print(f"SKIP (already in git_synced): {title}")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(wikitext)
        written += 1
        print(f"PULLED: {title}")

    print(f"\nCohort size (template-present, in [[Category:{CATEGORY}]]): {len(titles)}")
    print(f"Written to git_synced/: {written}")
    print(f"Skipped (already present): {skipped_existing}")


if __name__ == "__main__":
    main()
