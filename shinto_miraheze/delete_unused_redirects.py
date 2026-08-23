#!/usr/bin/env python3
"""
delete_unused_redirects.py
==========================
Walks ``Special:UnusedRedirects`` on shinto.miraheze.org and deletes
the redirect pages it lists. An "unused redirect" is a #REDIRECT
page that nothing on the wiki currently links to (no transclusions,
no wikilinks, no categorisation references) — keeping them around
just clutters the wiki without preserving any reachable history.

**Bail-loud safety policy.** ``Special:UnusedRedirects`` is a
querypage (cached, periodically rebuilt by the wiki) and historically
returns stale or empty data. Deleting based on bad data is
irreversible, so this script is paranoid:

  * If the querypage returns ZERO entries, bail without deleting
    anything. An empty answer is more often the cache being broken
    than a genuinely empty list.
  * For each candidate, refetch its current state and verify
    independently:
      - The page still exists.
      - It IS still a #REDIRECT (the leading wikitext starts with the
        redirect marker).
      - It has zero ``linkshere`` entries (no other page on the wiki
        links to it). The querypage is allowed to be wrong — the
        per-page check is the real authority.
  * Any per-page check that fails to fetch info → SKIP that page,
    don't delete. Fail-safe in the per-page direction even though we
    fail-loud at the global "empty list" check.

Standard CLI flags: ``--apply`` (default dry-run),
``--max-deletes`` (per-run cap, default 100),
``--run-tag`` (wiki-formatted run tag link for delete summaries).

No state file — the querypage IS the state. Each run pulls a fresh
list; deleted entries naturally drop off the next regeneration.
"""

import argparse
import io
import os
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
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5
READ_THROTTLE = 0.3
USER_AGENT = USER_AGENT

# MediaWiki querypage name. Must match the value the `qppage` API param
# accepts, which is the Special: alias in its exact casing — verified via
# api.php?action=paraminfo&modules=query+querypage (NOT a camel-stripped
# guess). For Special:UnusedRedirects the API requires "UnusedRedirects"
# (capital R). The previous "Unusedredirects" started returning
# ('badvalue', 'Unrecognized value for parameter "qppage"') ~2026-05-16,
# which failed this step and (because the cleanup job gates them on its
# success) silently blocked all daily Wikidata edits. The aliases are
# inconsistent per page — e.g. Listredirects has no capital R — so always
# confirm against paraminfo rather than by analogy with sibling scripts.
QUERYPAGE_NAME = "UnusedRedirects"


def iter_unused_redirects(site):
    """Yield titles from Special:UnusedRedirects via the querypage API."""
    params = {
        "list": "querypage",
        "qppage": QUERYPAGE_NAME,
        "qplimit": "max",
    }
    while True:
        data = site.api("query", **params)
        results = data.get("query", {}).get("querypage", {}).get("results", []) or []
        for entry in results:
            title = entry.get("title", "")
            if title:
                yield title
        if "continue" in data:
            params.update(data["continue"])
        else:
            break


def is_still_unused_redirect(site, title: str) -> tuple[bool, str]:
    """Return (ok_to_delete, reason). ok_to_delete=False with a clear
    reason when the per-page check rules a candidate out.

    The querypage is allowed to be wrong; this function is the real
    authority. We refuse to delete unless ALL three checks pass:
    page exists, page is currently a #REDIRECT, no other page links
    here.
    """
    # Single batched query: get page text + linkshere in one call.
    try:
        result = site.api(
            "query",
            titles=title,
            prop="revisions|linkshere",
            rvprop="content",
            rvslots="main",
            lhlimit="1",
            lhshow="!redirect",
            formatversion="2",
        )
    except Exception as e:
        return False, f"info refetch failed: {e}"

    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return False, "page query returned no entries"
    page = pages[0]
    if page.get("missing"):
        return False, "page no longer exists"
    revs = page.get("revisions") or []
    if not revs:
        return False, "no revisions in refetch"
    text = revs[0].get("slots", {}).get("main", {}).get("content", "")
    if not text.lstrip().lower().startswith("#redirect"):
        return False, "page is no longer a #REDIRECT"
    linkshere = page.get("linkshere") or []
    if linkshere:
        return False, f"now has {len(linkshere)}+ inbound link(s)"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply", action="store_true",
        help="Actually delete pages (default: dry-run reports only).",
    )
    ap.add_argument(
        "--max-deletes", type=int, default=100,
        help="Per-run cap on deletions (default 100).",
    )
    ap.add_argument(
        "--run-tag", required=True,
        help="Wiki-formatted run tag link for delete summaries.",
    )
    args = ap.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    print(f"Fetching Special:UnusedRedirects via querypage={QUERYPAGE_NAME!r} ...")
    candidates: list[str] = []
    for title in iter_unused_redirects(site):
        candidates.append(title)
    print(f"Querypage returned {len(candidates)} candidate(s)")

    # Bail-loud: empty querypage is more often the cache being broken
    # than a genuinely empty list. Refuse to mass-delete in either
    # interpretation.
    if not candidates:
        print(
            "BAIL: Querypage returned zero candidates. "
            "This is more often a cache failure than a genuinely empty list. "
            "No deletions will be performed.",
            file=sys.stderr,
        )
        return 0

    delete_reason_template = (
        "Deleting unused redirect (verified zero inbound links). {tag}"
    )

    deleted = checked = skipped = errors = 0
    for title in candidates:
        if args.apply and deleted >= args.max_deletes:
            print(f"Reached --max-deletes ({args.max_deletes}); stopping mid-run.")
            break
        checked += 1

        ok, reason = is_still_unused_redirect(site, title)
        time.sleep(READ_THROTTLE)
        if not ok:
            print(f"  SKIP {title}: {reason}")
            skipped += 1
            continue

        if not args.apply:
            print(f"  DRY {title}: would delete")
            deleted += 1
            continue

        try:
            page = site.pages[title]
            page.delete(
                reason=delete_reason_template.format(tag=args.run_tag).strip()
            )
            print(f"  DELETE {title}")
            deleted += 1
        except Exception as e:
            print(f"  ERROR {title}: delete failed: {e}")
            errors += 1
        time.sleep(THROTTLE)

    print(
        f"Done. checked={checked} "
        f"{'deleted' if args.apply else 'would-delete'}={deleted} "
        f"skipped={skipped} errors={errors}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
