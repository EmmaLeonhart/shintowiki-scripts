#!/usr/bin/env python3
"""
sunset_jp_char_count_cats.py
============================
One-shot action: adds ``[[Category:crud categories]]`` to each of the
"Pages with N+ untranslated japanese characters" bucket category
pages, marking the whole counter family for crud sunset.

The counter system was useful as a triage signal while we were still
draining `[[Category:Need translation]]`, but the bucket categories
themselves are wiki clutter — they aren't navigation, just diagnostic
state. Putting them into the crud-deletion pipeline lets the standard
sunset machinery remove them once the orchestrator op and the
standalone tagger stop adding the tags (both gated to no-op on or
after ``SUNSET_DATE = 2027-09-01`` — see ``untranslated_japanese`` op
and ``tag_untranslated_japanese.py``).

Walks the THRESHOLDS list from ``orchestrators/ops/untranslated_japanese.py``
so the two stay in sync. For each Category page that exists, appends
``[[Category:crud categories]]`` if not already present.

Standard flags: ``--apply`` (default dry-run), ``--max-edits``,
``--run-tag``.
"""

import argparse
import io
import os
import sys
import time

import mwclient
from wiki_login import login_with_retry

# Mirrors THRESHOLDS in
# shinto_miraheze/orchestrators/ops/untranslated_japanese.py. Inlined
# because this script runs as `python3 shinto_miraheze/X.py` (script
# dir on sys.path, not repo root; no shinto_miraheze/__init__.py), so
# the package import raises ModuleNotFoundError. Keep the two in sync.
THRESHOLDS = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
THROTTLE = 2.5
USER_AGENT = "SunsetJpCharCountCats/1.0 (User:EmmaBot; shinto.miraheze.org)"

CRUD_CAT = "[[Category:crud categories]]"


def category_titles() -> list[str]:
    return [
        f"Category:Pages with {t}+ untranslated japanese characters"
        for t in THRESHOLDS
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually save edits")
    ap.add_argument("--max-edits", type=int, default=50)
    ap.add_argument("--run-tag", default="manual run")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    login_with_retry(site, username, password)
    print(f"Logged in as {username}")

    edited = skipped = missing = errors = 0
    for title in category_titles():
        if args.apply and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping.")
            break

        try:
            page = site.pages[title]
            if not page.exists:
                print(f"  {title}: does not exist (skip)")
                missing += 1
                continue
            text = page.text()
        except Exception as e:
            print(f"  {title}: read error: {e}")
            errors += 1
            continue

        if CRUD_CAT in text:
            print(f"  {title}: already has crud-categories tag (skip)")
            skipped += 1
            continue

        new_text = text.rstrip() + "\n" + CRUD_CAT + "\n"
        summary = (
            f"sunset: mark counter category as crud for 2027-09-01 cleanup "
            f"{args.run_tag}"
        ).strip()

        if not args.apply:
            print(f"  DRY {title}: would append {CRUD_CAT}")
            edited += 1
            continue

        try:
            page.save(new_text, summary=summary, minor=False, bot=True)
            edited += 1
            print(f"  EDIT {title}: appended crud-categories tag")
        except Exception as e:
            print(f"  {title}: save error: {e}")
            errors += 1
        time.sleep(THROTTLE)

    print(
        f"Done. edited={edited} skipped={skipped} missing={missing} "
        f"errors={errors} of {len(THRESHOLDS)} categories"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
