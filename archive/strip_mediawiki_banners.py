#!/usr/bin/env python3
"""
strip_mediawiki_banners.py
===========================
One-shot sweep over ns=8 MediaWiki pages to strip the destructive
``<!-- History offloaded: ... -->`` banners (and other HTML-comment
cruft) that ``history_offload`` left behind. ns=8 is intentionally
excluded from every recurring orchestrator (per CLAUDE.md) because
interface messages there are too sensitive for generic space-saving
ops — but those same banners actively break MediaWiki interface
parsing, so this script exists as a targeted carve-out to undo the
damage.

Applies ``shinto_miraheze.orchestrators.ops.strip_html_comments`` to
every ns=8 page. The op itself has the banner-stripping logic and
respects ``history_offload``'s active-state for category pages
(irrelevant here — we're only walking ns=8).

Standard CLI shape: ``--apply`` (default dry-run), ``--max-edits``,
``--run-tag``. Stateful: tracks processed titles in
``strip_mediawiki_banners.state`` and resumes; clears the state file
when the sweep is fully exhausted.

Run locally or wire into a workflow step. Not an orchestrator op
because ns=8 doesn't have an orchestrator, and adding one just to
hold a single short-lived cleanup isn't worth the workflow plumbing.
"""

import argparse
import io
import os
import sys
import time

import mwclient

# This script is invoked as `python3 shinto_miraheze/X.py`, so the
# script directory — not the repo root — is sys.path[0], and there's
# no shinto_miraheze/__init__.py. Put the repo root on sys.path so the
# shinto_miraheze namespace package resolves; unlike the date/threshold
# constants elsewhere, the strip_html_comments op carries real logic
# that shouldn't be duplicated, so we fix the path instead of inlining.
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from shinto_miraheze.orchestrators.ops import strip_html_comments

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
THROTTLE = 2.5
USER_AGENT = "MediaWikiBannerStrip/1.0 (User:EmmaBot; shinto.miraheze.org)"
NAMESPACE = 8

STATE_FILE = os.path.join(
    os.path.dirname(__file__), "strip_mediawiki_banners.state"
)


def load_state() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_state(title: str) -> None:
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state() -> None:
    open(STATE_FILE, "w", encoding="utf-8").close()


def iter_mediawiki_pages(site):
    params = {"list": "allpages", "apnamespace": NAMESPACE, "aplimit": "max"}
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually save edits")
    ap.add_argument("--max-edits", type=int, default=50)
    ap.add_argument("--run-tag", default="manual run", help="appended to summary")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.login(username, password)
    print(f"Logged in as {username}")

    done = load_state() if args.apply else set()
    print(f"State: {len(done)} ns=8 titles already processed")

    edited = checked = errors = 0
    finished_all = True

    for title in iter_mediawiki_pages(site):
        if args.apply and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping mid-cycle.")
            finished_all = False
            break
        if title in done:
            continue
        checked += 1

        try:
            page = site.pages[title]
            if not page.exists:
                if args.apply:
                    append_state(title)
                continue
            text = page.text()
        except Exception as e:
            print(f"  {title}: read error: {e}")
            errors += 1
            if args.apply:
                append_state(title)
            continue

        try:
            new_text, summary = strip_html_comments.apply(title, text)
        except Exception as e:
            print(f"  {title}: apply error: {e}")
            errors += 1
            if args.apply:
                append_state(title)
            continue

        if new_text is None:
            if args.apply:
                append_state(title)
            continue

        full_summary = f"{summary} {args.run_tag}".strip()
        if not args.apply:
            print(f"  DRY {title}: would strip ({len(text) - len(new_text)} bytes)")
            edited += 1
            continue

        try:
            page.save(new_text, summary=full_summary, minor=False, bot=True)
            edited += 1
            print(f"  EDIT {title}: stripped ({len(text) - len(new_text)} bytes)")
        except Exception as e:
            print(f"  {title}: save error: {e}")
            errors += 1
        append_state(title)
        time.sleep(THROTTLE)

    print(
        f"Done. checked={checked} edited={edited} errors={errors} "
        f"finished_all={finished_all}"
    )
    if args.apply and finished_all:
        clear_state()
        print("State cleared (sweep complete).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
