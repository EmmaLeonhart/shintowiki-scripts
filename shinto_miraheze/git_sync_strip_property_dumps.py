#!/usr/bin/env python3
"""
git_sync_strip_property_dumps.py
================================
Emma 2026-07-06: the Wikidata-generated shikinaisha pages carry a raw Wikidata
property dump (a run of ``== <property> (Pxxx) ==`` second-level sections) on top
of the real translated article. That property dump "just goes away" — the
infobox and the categories are valuable and stay. Emma tags the pages to fix into
``[[Category:sync these pages now]]`` and wants them made into git-synced pages.

This script pulls every page in ``[[Category:sync these pages now]]`` into
``git_synced/``, STRIPS the property-dump sections, retags (drops the transient
``sync these pages now`` tag, adds ``[[Category:Git synced pages]]`` so the
existing repo-wins sync pushes the cleaned page + tracks it), and writes the
local file. ``sync_git_synced_pages.py`` (already in CI) then pushes to the wiki.

The strip is DETERMINISTIC and surgical: a section whose heading matches
``== … (P<digits>) ==`` plus its bullet/blank body is removed; it stops at the
first non-bullet line (another heading, ``[[ja:…]]``, ``{{wikidata link}}``,
``== Japanese content ==``, prose), so the infobox, interwiki, wikidata link, the
real article, and all categories are untouched.

Read-only on the wiki. ``--apply`` writes local files; default dry-run reports
stats + flags any page that would strip suspiciously (safety before touching many
pages). ``--max`` caps pages this run.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GIT_SYNCED = os.path.join(REPO_ROOT, "git_synced")
API = "https://shinto.miraheze.org/w/api.php"
UA = USER_AGENT
SOURCE_CATEGORY = "sync these pages now"
GIT_SYNCED_TAG = "[[Category:Git synced pages]]"
THROTTLE = 0.3

PROP_HEADING = re.compile(r"^==+\s*.*\(P\d+\).*==+\s*$")
SYNC_NOW_RE = re.compile(r"\[\[\s*Category\s*:\s*sync these pages now\s*(?:\|[^\]]*)?\]\]\n?",
                         re.IGNORECASE)
GIT_SYNCED_RE = re.compile(r"\[\[\s*Category\s*:\s*Git synced pages\s*\]\]", re.IGNORECASE)


def strip_property_dump(text: str) -> str:
    """Remove every ``== … (Pxxx) ==`` section (heading + its blank/bullet body).
    Stops skipping at the first non-blank, non-bullet line so nothing else is
    touched."""
    out = []
    skip = False
    for ln in text.split("\n"):
        if PROP_HEADING.match(ln):
            skip = True
            continue
        if skip:
            s = ln.strip()
            if s == "" or s.startswith(("*", ":")):
                continue
            skip = False
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def retag(text: str) -> str:
    """Drop the transient sync-now tag; ensure the git-synced tag is present."""
    text = SYNC_NOW_RE.sub("", text)
    if not GIT_SYNCED_RE.search(text):
        text = text.rstrip() + "\n\n" + GIT_SYNCED_TAG + "\n"
    return text


def title_to_filename(title: str) -> str:
    return title.replace(":", "%3A").replace("/", "%2F") + ".wiki"


def _get_json(params: dict, post: bool = False):
    for attempt in range(4):
        try:
            if post:
                r = urllib.request.urlopen(urllib.request.Request(
                    API, data=urllib.parse.urlencode(params).encode(),
                    headers={"User-Agent": UA}), timeout=60)
            else:
                r = urllib.request.urlopen(urllib.request.Request(
                    API + "?" + urllib.parse.urlencode(params),
                    headers={"User-Agent": UA}), timeout=60)
            import json
            return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def category_members(category=SOURCE_CATEGORY):
    mem, cont = [], {}
    while True:
        p = {"action": "query", "list": "categorymembers",
             "cmtitle": "Category:" + category, "cmlimit": "500",
             "cmtype": "page", "format": "json"}
        p.update(cont)
        d = _get_json(p)
        if not d:
            break
        mem += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" in d:
            cont = d["continue"]
            time.sleep(0.2)
        else:
            break
    return mem


def fetch_contents(titles):
    out = {}
    for i in range(0, len(titles), 40):
        d = _get_json({"action": "query", "titles": "|".join(titles[i:i + 40]),
                       "prop": "revisions", "rvprop": "content", "rvslots": "main",
                       "formatversion": "2", "format": "json"}, post=True)
        if not d:
            continue
        for pg in d.get("query", {}).get("pages", []):
            if pg.get("missing"):
                continue
            out[pg["title"]] = pg["revisions"][0]["slots"]["main"]["content"]
        time.sleep(THROTTLE)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write git_synced/ files.")
    ap.add_argument("--max", type=int, default=100000)
    ap.add_argument("--category", default=SOURCE_CATEGORY,
                    help="Category to process (default the sync-now trigger; pass "
                         "'Wikidata generated shikinaisha pages' to do the full set).")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    os.makedirs(GIT_SYNCED, exist_ok=True)

    titles = category_members(args.category)[: args.max]
    print(f"Pages in [[Category:{args.category}]]: {len(titles)}")
    contents = fetch_contents(titles)
    print(f"Fetched: {len(contents)}")

    written = flagged = no_dump = 0
    flags = []
    for title, text in contents.items():
        n_props = len(PROP_HEADING.findall(text.replace("\n", "\n")))
        n_props = sum(1 for ln in text.split("\n") if PROP_HEADING.match(ln))
        stripped = strip_property_dump(text)
        final = retag(stripped)
        if n_props == 0:
            no_dump += 1
        # Safety: only flag a genuinely-gutted result — one that kept NEITHER an
        # infobox NOR a redirect (legit small pages are redirects/stubs, e.g.
        # Wakasa-hime is a #REDIRECT and correctly stays small).
        if ("{{Infobox" not in final and "REDIRECT" not in final.upper()
                and len(final) < 600):
            flags.append((title, len(text), len(final)))
            flagged += 1
            continue
        if args.apply:
            with open(os.path.join(GIT_SYNCED, title_to_filename(title)),
                      "w", encoding="utf-8", newline="\n") as f:
                f.write(final)
        written += 1

    print(f"\nWould write: {written} | flagged (skipped, review): {flagged} | "
          f"had no property dump: {no_dump}")
    for t, a, b in flags[:15]:
        print(f"  FLAG {t}: {a}B -> {b}B")
    if not args.apply:
        print("\n[DRY] pass --apply to write git_synced/ files")


if __name__ == "__main__":
    main()
