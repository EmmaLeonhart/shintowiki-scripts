#!/usr/bin/env python3
"""Pull every page in [[Category:Pages with deleted QID in ill template]] into the
local ``git_synced/`` directory so its ``{{ill|…|qid=DELETED_QID}}`` templates can be
edited HERE (fix sub-topic ills → section links, recreate real entities, relink
duplicates). Emma 2026-07-06: "you just copy the page markdown into the repo and add
the git synced pages category at the bottom of it."

Mechanism: ``git_synced/<title>.wiki`` = the page's current wikitext + a
``[[Category:Git synced pages]]`` tag at the bottom. `sync_git_synced_pages.py`
(already in CI, repo-wins) then pushes the tag to the wiki and keeps the page in
sync. Git-sync is TEMPORARY — once a page's ills are resolved, remove the category
tag from the local file and the next sync drops both the on-wiki category and the
local copy.

Read-only against the wiki (writes only local files); no wiki credentials needed.
Skips a page whose wikitext already carries the category, and never clobbers an
existing git_synced/ file.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.title_filename import title_to_filename  # noqa: E402
import io
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GIT_SYNCED = os.path.join(REPO, "git_synced")
API = "https://shinto.miraheze.org/w/api.php"
UA = USER_AGENT
CATEGORY = "Pages with deleted QID in ill template"
TAG = "[[Category:Git synced pages]]"
# Must match sync_git_synced_pages.title_to_filename so the sync maps file↔title.


NOTE = ("<!-- [git-synced 2026-07-06] Pulled for deleted-QID ill resolution: fix "
        "sub-topic {{ill|…|qid=DELETED_QID}} templates (→ section links where they are "
        "really sections, recreate real entities by hand, relink duplicates). Remove "
        "this category once the page's ills are resolved and the next sync will drop "
        "the local copy. -->")


def _get(params):
    for attempt in range(4):
        r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 429:
            print("  [429] bailing per policy")
            sys.exit(2)
        if r.status_code >= 500:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    return None


def category_members():
    out, cont = [], {}
    while True:
        p = {"action": "query", "list": "categorymembers", "cmtitle": "Category:" + CATEGORY,
             "cmtype": "page", "cmlimit": "500", "format": "json"}
        p.update(cont)
        r = _get(p)
        out += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
        if "continue" in r:
            cont = r["continue"]; time.sleep(0.3)
        else:
            return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    titles = category_members()
    print(f"Pages in [[Category:{CATEGORY}]]: {len(titles)}")
    written = skipped = 0
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        r = _get({"action": "query", "titles": "|".join(batch), "prop": "revisions",
                  "rvprop": "content", "rvslots": "main", "formatversion": "2", "format": "json"})
        for pg in r.get("query", {}).get("pages", []):
            if pg.get("missing"):
                continue
            title = pg["title"]
            text = pg["revisions"][0]["slots"]["main"]["content"]
            path = os.path.join(GIT_SYNCED, title_to_filename(title))
            if os.path.exists(path):
                skipped += 1
                continue
            body = text.rstrip("\n")
            if TAG not in body:
                body = body + "\n\n" + NOTE + "\n" + TAG
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(body + "\n")
            written += 1
        time.sleep(0.3)
    print(f"Wrote {written} git_synced/*.wiki files; skipped {skipped} (already present).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
