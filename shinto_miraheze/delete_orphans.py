#!/usr/bin/env python3
"""
delete_orphans.py
=================
Monthly bot job: delete subject-side orphan pages from
shinto.miraheze.org. Orphans here = members of
``Special:LonelyPages`` — mainspace pages with zero incoming
wikilinks. The (already-shipped) ``delete_orphaned_talk_pages.py``
handles the OTHER orphan flavour (talk pages without a subject); this
script handles the subject side.

Default definition is the conservative "Special:LonelyPages alone"
choice from the queue item — if Emma wants tighter rules later
(LonelyPages AND uncategorised, or LonelyPages AND not transcluded,
or LonelyPages AND older than N days), wire those in as additional
filters in ``_should_delete``.

Safeguards (baked in):

* Never delete Main Page.
* Skip redirects (Special:LonelyPages typically excludes them, but
  double-check before deleting).
* Skip any page tagged ``[[Category:Do not delete]]`` — opt-out.
* Mainspace (ns=0) only — Special:LonelyPages returns mainspace by
  default, but we filter defensively.

Standard CLI: ``--apply`` (default dry-run), ``--max-deletes`` (per-run
cap), ``--run-tag``. Wiki auth via ``WIKI_USERNAME`` + ``WIKI_PASSWORD``
env vars (the bot-password format ``EmmaBot@EmmaBot``).

Pacing: ``THROTTLE = 2.5`` between delete API calls (the project-wide
wiki-load throttle from CLAUDE.md). Read-only API calls between deletes
are not throttled — they're inexpensive.

Invoked from ``.github/workflows/delete-orphans.yml`` on a monthly cron
(``7 5 1 * *`` — 05:07 UTC on the 1st of each month). First fire:
2026-06-01.
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
import sys
import time

import mwclient
from wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

# Hard exclusions — never delete these no matter what Special:LonelyPages
# says. Add to this set if specific pages need bulletproof protection
# beyond the Category:Do not delete opt-out.
HARD_EXCLUDES: set[str] = {"Main Page"}

# Opt-out category. A page carrying this category is never touched,
# even if Special:LonelyPages lists it.
OPT_OUT_CATEGORY = "Do not delete"


def iter_lonely_pages(site):
    """Yield (title, namespace) for every page on Special:LonelyPages.

    ``list=querypage&qppage=Lonelypages`` is the MediaWiki API for this
    special page. Note the casing: it's ``Lonelypages`` (lowercase
    second word), NOT ``LonelyPages`` — verified against the wiki's
    ``action=paraminfo&modules=query%2Bquerypage`` output 2026-05-27.
    The casing-convention is NOT uniform across querypages
    (``OrphanedTalkPages`` is camelcase; ``Lonelypages`` isn't), so
    rely on paraminfo, not historical convention. See
    ``feedback_qppage_casing.md`` in user memory.

    Results are cached server-side and refresh on the wiki's regular
    maintenance cadence — re-running the script immediately after a
    deletion may still see the just-deleted page in the list for a
    while, which is why we check ``page.exists`` before attempting to
    delete."""
    params = {
        "list": "querypage",
        "qppage": "Lonelypages",
        "qplimit": "max",
    }
    while True:
        data = site.api("query", **params)
        entries = data.get("query", {}).get("querypage", {}).get(
            "results", []
        )
        for entry in entries:
            title = entry.get("title", "")
            ns = entry.get("ns", 0)
            if title:
                yield title, ns
        if "continue" in data:
            params.update(data["continue"])
        else:
            break


def _has_opt_out_category(page) -> bool:
    """True if the page carries ``[[Category:Do not delete]]``."""
    try:
        for cat in page.categories():
            # mwclient yields Page objects for each category;
            # cat.name is "Category:<name>" — strip the prefix.
            name = cat.name
            if name.startswith("Category:"):
                name = name[len("Category:"):]
            if name == OPT_OUT_CATEGORY:
                return True
    except Exception:
        # Fail safe: if we can't determine, treat as opt-out (don't
        # delete). Better to skip a real orphan than delete a page
        # that might have been protected and we couldn't verify.
        return True
    return False


def _should_delete(page, title: str, ns: int) -> tuple[bool, str]:
    """Return (delete?, reason). Reason describes the skip when not
    deleting, or the green-light when deleting."""
    if title in HARD_EXCLUDES:
        return False, f"HARD_EXCLUDE ({title!r})"
    if ns != 0:
        return False, f"non-mainspace (ns={ns})"
    if not page.exists:
        return False, "page does not exist (stale querypage cache)"
    if page.redirect:
        return False, "is a redirect"
    if _has_opt_out_category(page):
        return False, f"has [[Category:{OPT_OUT_CATEGORY}]] opt-out"
    return True, "LonelyPages member, no safeguard hits"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="actually delete; default is dry-run (report only)",
    )
    parser.add_argument(
        "--max-deletes", type=int, default=50,
        help="per-run cap on deletions (default 50)",
    )
    parser.add_argument(
        "--run-tag", required=True,
        help="wiki-formatted run tag link for delete-summary attribution",
    )
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT,
    )
    if args.apply:
        if not PASSWORD:
            print("FATAL: --apply requires WIKI_PASSWORD env var.",
                  file=sys.stderr)
            return 2
        login_with_retry(site, USERNAME, PASSWORD)
        print(f"Logged in as {USERNAME}")
    else:
        print("DRY RUN — no login, no deletes")

    print(f"Walking Special:LonelyPages (cap: {args.max_deletes} deletes)")
    print()

    checked = deleted = skipped = errors = 0
    for title, ns in iter_lonely_pages(site):
        if deleted >= args.max_deletes:
            print(f"\nReached max-deletes ({args.max_deletes}); stopping.")
            break

        checked += 1
        page = site.pages[title]
        prefix = f"[{checked}] {title}"

        ok, reason = _should_delete(page, title, ns)
        if not ok:
            print(f"{prefix} SKIP ({reason})")
            skipped += 1
            continue

        if not args.apply:
            print(f"{prefix} DRY: would delete ({reason})")
            deleted += 1  # count would-deletes for the cap
            continue

        try:
            page.delete(
                reason=f"Bot: delete orphan (Special:LonelyPages) {args.run_tag}"
            )
            deleted += 1
            print(f"{prefix} DELETED")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"{prefix} ERROR deleting: {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"Mode:    {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Checked: {checked}")
    print(f"Deleted: {deleted}{'' if args.apply else ' (would-delete count)'}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
