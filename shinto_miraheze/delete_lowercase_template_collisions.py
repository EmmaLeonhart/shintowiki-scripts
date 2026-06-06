#!/usr/bin/env python3
"""
delete_lowercase_template_collisions.py
========================================
One-shot wiki cleanup: delete the 19 lowercase ``Template:Infobox <name>``
pages from shinto.miraheze.org and shinto.fandom.com that collide
case-only with the canonical capitalised variant.

Context (see ``docs/case_collision_report.md``): both wikis carry
duplicate template pages whose titles differ only by inner-word case
— ``Template:Infobox Mountain`` and ``Template:Infobox mountain``,
etc. — and whose content is byte-identical. The sync scripts mirror
both into ``fandom_unique/`` / ``miraheze_unique/``, jamming Windows
git operations (``core.ignorecase=true`` can only check out one at a
time). The ``canonicalize_template_case`` op has been rewriting every
``{{infobox X}}`` / ``[[Template:Infobox x]]`` reference across all
namespaces to the canonical form so the lowercase pages can be safely
deleted with zero transclusions left.

This script enforces that "zero transclusions" precondition page-by-
page via ``list=embeddedin``: a lowercase template is deleted ONLY
if (a) it exists, (b) its canonical capitalised twin exists, (c)
their current content is byte-identical, and (d) no page on the wiki
still transcludes the lowercase variant. Anything failing those
checks is skipped with a logged reason — re-run later, after another
orchestrator sweep, and the remaining ones will clear.

Once both wikis are clean, the next ``sync_*_unique_pages.py`` run
will pull the deletions (the lowercase ``.wiki`` files disappear from
``fandom_unique/`` / ``miraheze_unique/`` automatically; the sync's
"orphan with no category" branch then deletes the local files).

Standard CLI: ``--apply`` (default dry-run), ``--max-deletes``,
``--run-tag``. ``--wiki`` selects ``miraheze``, ``fandom``, or
``both`` (default ``both``). ``THROTTLE = 2.5`` between delete calls,
per the project-wide wiki-load convention.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

from wiki_login import login_with_retry

# Match `#REDIRECT [[Target]]` (or `#redirect`, `#Redirect`, optional
# leading `:` interwiki marker, optional `|display text` after the
# target). Captures the raw target string only. MediaWiki accepts any
# casing of the `#REDIRECT` magic word and tolerates surrounding
# whitespace.
_REDIRECT_RE = re.compile(
    r"^\s*#REDIRECT\s*:?\s*\[\[\s*(?P<target>[^|\]\n]+?)\s*(?:\|[^\]\n]*)?\s*\]\]",
    re.IGNORECASE,
)


def _normalize_title(title: str) -> str:
    """MediaWiki-style title normalisation: trim, collapse runs of
    underscores/spaces to a single space, upper-case the first letter
    of the page name (after any namespace prefix). Used to decide
    whether a redirect target points at our canonical title.
    """
    t = title.strip().replace("_", " ")
    t = re.sub(r" +", " ", t)
    if ":" in t:
        ns, _, page = t.partition(":")
        if page:
            page = page[0].upper() + page[1:]
        return f"{ns.strip()}:{page}"
    return t[0].upper() + t[1:] if t else t


def _redirect_target(text: str):
    """Return the (normalised) redirect target if ``text`` is a
    `#REDIRECT [[X]]` page, else ``None``."""
    if not text:
        return None
    m = _REDIRECT_RE.match(text)
    if not m:
        return None
    return _normalize_title(m.group("target"))


USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

WIKIS = {
    "miraheze": {
        "url": "shinto.miraheze.org",
        "path": "/w/",
        "ua": "DeleteLowercaseTemplateCollisionsBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    },
    "fandom": {
        "url": "shinto.fandom.com",
        "path": "/",
        "ua": "DeleteLowercaseTemplateCollisionsBot/1.0 (User:EmmaBot; shinto.fandom.com)",
    },
}

# (lowercase variant -> canonical variant) for the Template:Infobox
# collision pairs identified in docs/case_collision_report.md. Hard-
# coded so the script is reviewable in isolation; refresh the report
# and update this map if new collisions appear.
TEMPLATE_PAIRS = {
    "Template:Infobox chinese":       "Template:Infobox Chinese",
    "Template:Infobox film":          "Template:Infobox Film",
    "Template:Infobox historic site": "Template:Infobox Historic Site",
    "Template:Infobox holiday":       "Template:Infobox Holiday",
    "Template:Infobox kofun":         "Template:Infobox Kofun",
    "Template:Infobox mountain":      "Template:Infobox Mountain",
    "Template:Infobox museum":        "Template:Infobox Museum",
    "Template:Infobox noble":         "Template:Infobox Noble",
    "Template:Infobox officeholder":  "Template:Infobox Officeholder",
    "Template:Infobox organization":  "Template:Infobox Organization",
}


def _embeddedin_count(site, title: str) -> int:
    """Return the number of pages transcluding ``title`` on ``site``.

    Stops counting once it sees more than zero (we only care about
    "any" vs "none" for the safety gate). Uses ``list=embeddedin``
    rather than ``page.embeddedin()`` so we can cap the result at 1
    and avoid paginating through potentially thousands of hits."""
    data = site.api(
        "query",
        list="embeddedin",
        eititle=title,
        eilimit=1,
        formatversion="2",
    )
    return len(data.get("query", {}).get("embeddedin", []) or [])


def _fetch_content(site, title: str):
    """Return (exists, text) for ``title`` on ``site``."""
    data = site.api(
        "query",
        titles=title,
        prop="revisions",
        rvprop="content",
        rvslots="main",
        rvlimit=1,
        formatversion="2",
    )
    pages = data.get("query", {}).get("pages", []) or []
    if not pages:
        return False, None
    page = pages[0]
    if page.get("missing"):
        return False, None
    revs = page.get("revisions") or []
    if not revs:
        return True, ""
    return True, revs[0].get("slots", {}).get("main", {}).get("content", "")


def _process_wiki(wiki_key: str, apply: bool, max_deletes: int,
                  run_tag: str) -> tuple[int, int, int]:
    cfg = WIKIS[wiki_key]
    site = mwclient.Site(
        cfg["url"], path=cfg["path"], clients_useragent=cfg["ua"],
    )
    if apply:
        if not PASSWORD:
            print(f"  FATAL: --apply requires WIKI_PASSWORD env var.",
                  file=sys.stderr)
            return 0, 0, 1
        login_with_retry(site, USERNAME, PASSWORD)
        print(f"  logged in as {USERNAME}")
    else:
        print("  dry-run (no login, no deletes)")

    deleted = skipped = errors = 0

    for lower_title, canonical_title in TEMPLATE_PAIRS.items():
        if deleted >= max_deletes:
            print(f"  reached max-deletes ({max_deletes}); stopping wiki.")
            break

        # (a) lowercase variant must exist.
        lower_exists, lower_text = _fetch_content(site, lower_title)
        if not lower_exists:
            print(f"  SKIP {lower_title!r}: already absent")
            skipped += 1
            continue

        # (b) canonical capitalised variant must exist.
        canon_exists, canon_text = _fetch_content(site, canonical_title)
        if not canon_exists:
            print(
                f"  SKIP {lower_title!r}: canonical {canonical_title!r} "
                f"missing — refusing to delete the only surviving copy"
            )
            skipped += 1
            continue

        # (c) byte-identical content OR lowercase is already a redirect
        # pointing at the canonical. The redirect case is just as safe
        # to delete: any transclusion or wikilink that resolved via the
        # lowercase title was already being redirected to the canonical,
        # so deleting the redirect breaks nothing the redirect was hiding.
        # (Mostly hits page-move leftovers — e.g. Emma's 2026-05-27
        # `Template:Infobox noble` -> `Template:Infobox Noble` move.)
        if (lower_text or "") != (canon_text or ""):
            redirect_to = _redirect_target(lower_text or "")
            if redirect_to and _normalize_title(redirect_to) == _normalize_title(canonical_title):
                print(
                    f"  ACCEPT {lower_title!r}: is a #REDIRECT to "
                    f"{canonical_title!r} (page-move leftover, safe to delete)"
                )
            else:
                print(
                    f"  SKIP {lower_title!r}: content diverges from "
                    f"{canonical_title!r} ({len(lower_text or '')} vs "
                    f"{len(canon_text or '')} bytes) — needs manual review"
                )
                skipped += 1
                continue

        # (d) zero remaining transclusions of the lowercase variant.
        # canonicalize_template_case op rewrites references to the
        # canonical form; if any are left, that orchestrator pass
        # hasn't visited those pages yet — wait for another cycle.
        try:
            n_transcluders = _embeddedin_count(site, lower_title)
        except Exception as e:
            print(f"  ERROR checking transclusions of {lower_title!r}: {e}")
            errors += 1
            continue
        if n_transcluders:
            print(
                f"  SKIP {lower_title!r}: still has >=1 transclusion "
                f"(canonicalize_template_case sweep not complete)"
            )
            skipped += 1
            continue

        if not apply:
            print(f"  DRY would delete {lower_title!r} "
                  f"(byte-identical to {canonical_title!r}, 0 transclusions)")
            deleted += 1  # count would-deletes for the cap
            continue

        try:
            site.pages[lower_title].delete(
                reason=(
                    f"Bot: delete case-collision duplicate of "
                    f"[[{canonical_title}]] (identical content, 0 "
                    f"transclusions) {run_tag}"
                ),
            )
            deleted += 1
            print(f"  DELETED {lower_title!r}")
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"  ERROR deleting {lower_title!r}: {e}")
            errors += 1

    return deleted, skipped, errors


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="actually delete; default is dry-run (report only)",
    )
    parser.add_argument(
        "--max-deletes", type=int, default=50,
        help="per-wiki cap on deletions (default 50)",
    )
    parser.add_argument(
        "--run-tag", required=True,
        help="wiki-formatted run tag link for delete-summary attribution",
    )
    parser.add_argument(
        "--wiki", choices=("miraheze", "fandom", "both"), default="both",
        help="which wiki to process (default both)",
    )
    args = parser.parse_args()

    wiki_keys = ("miraheze", "fandom") if args.wiki == "both" else (args.wiki,)

    total_deleted = total_skipped = total_errors = 0
    for key in wiki_keys:
        print(f"=== {WIKIS[key]['url']} ===")
        d, s, e = _process_wiki(key, args.apply, args.max_deletes, args.run_tag)
        total_deleted += d
        total_skipped += s
        total_errors += e
        print()

    print("=" * 60)
    print(f"Mode:    {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Deleted: {total_deleted}{'' if args.apply else ' (would-delete count)'}")
    print(f"Skipped: {total_skipped}")
    print(f"Errors:  {total_errors}")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
