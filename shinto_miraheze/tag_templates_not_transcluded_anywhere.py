#!/usr/bin/env python3
"""
tag_templates_not_transcluded_anywhere.py
==========================================
Walks ``[[Category:Templates not transcluded in mainspace]]`` and, for
each template, checks whether it's transcluded in category space
(ns=14) either. If neither, adds
``[[Category:Templates not transcluded in mainspace or categoryspace]]``
to the template page.

The narrower "in mainspace or categoryspace" signal is what we
actually want for crud-deletion: templates only used inside category
pages (e.g., shrine-region nav templates) are worth keeping, but
templates with zero transclusions in *either* of the two
content-bearing namespaces really are wiki-space waste.

After this sweep is settled, a separate one-shot tags the older
"in mainspace" category as crud (see
``sunset_templates_not_transcluded_in_mainspace_cat.py``, intended to
run on/after 2027-07-01 per the queue plan), and the new "in mainspace
or categoryspace" category becomes the working surface for deletions.

Standard flags: ``--apply`` (default dry-run), ``--max-edits``,
``--run-tag``. Stateful via ``.state`` file; clears state when
sweep is fully exhausted.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.user_agent import USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
THROTTLE = 2.5
USER_AGENT = USER_AGENT

SOURCE_CATEGORY = "Templates not transcluded in mainspace"
NEW_CATEGORY = "Templates not transcluded in mainspace or categoryspace"
NEW_CAT_TAG = f"[[Category:{NEW_CATEGORY}]]"
CATEGORY_NAMESPACE = 14

STATE_FILE = os.path.join(
    os.path.dirname(__file__), "tag_templates_not_transcluded_anywhere.state"
)

# Match the new-cat tag whether or not surrounding whitespace varies.
NEW_CAT_RE = re.compile(
    rf"\[\[\s*Category\s*:\s*{re.escape(NEW_CATEGORY)}\s*\]\]",
    re.IGNORECASE,
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


def iter_category_members(site, category: str):
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "max",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("categorymembers", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def has_category_transclusions(site, template_title: str) -> bool:
    """True iff the template is embedded in at least one ns=14 page."""
    params = {
        "list": "embeddedin",
        "eititle": template_title,
        "einamespace": str(CATEGORY_NAMESPACE),
        "eilimit": "1",
        "eifilterredir": "nonredirects",
    }
    result = site.api("query", **params)
    return bool(result.get("query", {}).get("embeddedin", []))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually save edits")
    ap.add_argument("--max-edits", type=int, default=100)
    ap.add_argument("--run-tag", default="manual run")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    login_with_retry(site, username, password)
    print(f"Logged in as {username}")

    done = load_state() if args.apply else set()
    print(f"State: {len(done)} templates already processed")

    edited = checked = skipped = errors = 0
    finished_all = True

    for title in iter_category_members(site, SOURCE_CATEGORY):
        if args.apply and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping mid-sweep.")
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
            in_cat_ns = has_category_transclusions(site, title)
        except Exception as e:
            print(f"  {title}: embeddedin check error: {e}")
            errors += 1
            if args.apply:
                append_state(title)
            time.sleep(0.3)
            continue
        time.sleep(0.3)  # throttle the read-only check too

        if in_cat_ns:
            # Used in category space — keep it.
            if args.apply:
                append_state(title)
            skipped += 1
            continue

        if NEW_CAT_RE.search(text):
            # Already tagged.
            if args.apply:
                append_state(title)
            skipped += 1
            continue

        new_text = text.rstrip() + "\n" + NEW_CAT_TAG + "\n"
        summary = (
            f"tag as not transcluded in mainspace or categoryspace "
            f"{args.run_tag}"
        ).strip()

        if not args.apply:
            print(f"  DRY {title}: would append {NEW_CAT_TAG}")
            edited += 1
            continue

        try:
            page.save(new_text, summary=summary, minor=False, bot=True)
            edited += 1
            print(f"  EDIT {title}: tagged")
        except Exception as e:
            print(f"  {title}: save error: {e}")
            errors += 1
        append_state(title)
        time.sleep(THROTTLE)

    print(
        f"Done. checked={checked} edited={edited} skipped={skipped} "
        f"errors={errors} finished_all={finished_all}"
    )
    if args.apply and finished_all:
        clear_state()
        print("State cleared (sweep complete).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
