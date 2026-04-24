"""
history_offload op
===================
Archives a page's full revision history to (a) the XML archive repo and
(b) shinto.fandom.com, then deletes + recreates the source page so the
old revisions move into MediaWiki's per-title "deleted edits" pool. The
result on shintowiki is a single visible revision (a banner + current
content) with a "View or undelete N deleted edits" link above the history,
rather than inline "(username removed)" rows from per-revision hiding.

Safety:
  * Runs only when ENABLE_HISTORY_OFFLOAD=1 (env var). Otherwise the op is
    a no-op so it can safely sit at the top of every orchestrator OPS list.
  * Order: fandom mirror → XML archive → delete → recreate. Each step is
    gated on the previous succeeding, so a crash leaves either (a) nothing
    changed, (b) a harmless archive file / fandom import, or (c) a deleted
    page that needs Special:Undelete + manual recreate to restore.
  * The destructive delete+recreate runs only when ENABLE_REVDEL=1 (the
    gate is named for historical reasons — we used to revdel here, now we
    delete+recreate for a cleaner page-history UI).
  * ENABLE_FANDOM_MIRROR=1 additionally makes a fandom mirror required;
    if the mirror fails, the op aborts for that page and nothing
    destructive happens.

Skip conditions:
  * If the page is already in its offloaded steady state (banner present
    AND only 1 visible revision), the op returns early without touching it.
  * If the page has only 1 revision total, there is no history worth
    offloading, so the op skips.

Why delete+recreate rather than action=revisiondelete:
  * Revisiondelete renders every hidden revision inline as
    "(username removed) ... (edit summary removed)", which clutters the
    page history indefinitely.
  * Delete+recreate produces MediaWiki's "View or undelete N deleted edits"
    link — one line above a clean single-revision history.
  * Tradeoff: page-delete clears the page ID (new ID on recreate) and
    forces the link table to re-evaluate every incoming link. Both are
    acceptable given the user-facing UI is the priority.

The op sets HANDLES_SAVE = True, which tells common.run_orchestrator to
run it in a pre-pass and then refetch page.text() before the regular
apply() ops see the page — so downstream per-page ops act on the
recreated banner-only version.
"""

import os
import re
import urllib.parse

from . import _archive_repo, fandom_mirror

NAME = "history_offload"

# Belt-and-suspenders redirect guard. common.run_orchestrator already
# skips redirects before any op runs, but offloading a redirect page's
# history is never correct (there's nothing to preserve and the delete
# + recreate cycle would trash the redirect), so we refuse again here
# in case this op is ever invoked outside the orchestrator or the
# common-loop check is bypassed. Matches hard #REDIRECT and the common
# soft/category redirect templates.
_REDIRECT_RE = re.compile(
    r"^\s*("
    r"#redirect\b"
    r"|\{\{\s*(?:category|soft)[\s_]*redirect\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
# Every wikitext-content namespace. Excludes virtual (-2/-1) and special-
# content namespaces where wikitext edits don't apply: GeoJson (420),
# Module/Scribunto (828), and Wikibase Item/Property (860/862). Their Talk
# counterparts (421/829/861/863) ARE wikitext and are included.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)
HANDLES_SAVE = True

VIEWER_URL = "https://emmaleonhart.github.io/shintowiki-scripts/wikihistory.html"
SUMMARY_LIMIT = 500
COMMENT_MARKER = "<!-- History offloaded:"


def _viewer_link(title: str) -> str:
    page = urllib.parse.quote(title.replace(" ", "_"), safe="_")
    return f"{VIEWER_URL}?page={page}"


def _top_comment(title: str, run_tag: str) -> str:
    link = _viewer_link(title)
    return (
        f"{COMMENT_MARKER} due to miraheze stability concerns, the edit "
        f"history of this page has been offloaded to the XML archive. "
        f"See {link} for full history. Last refreshed: {run_tag} -->"
    )


def _build_summary(title: str, contributors: list[str], run_tag: str) -> str:
    link = _viewer_link(title)
    prefix = (
        "[[Project:History cleanup|Offloading history due to miraheze "
        "stability concerns]]"
    )
    suffix = f", see [{link} here] for full history {run_tag}"

    def attempt(contrib_text: str) -> str:
        return f"{prefix} {contrib_text}{suffix}"

    if contributors:
        joined = ", ".join(f"[[User:{u}]]" for u in contributors)
        full = attempt(f"previous contributors were {joined}")
        if len(full) <= SUMMARY_LIMIT:
            return full
    return attempt("many contributors")


def _strip_existing_banner(text: str) -> str:
    """Remove a prior history_offload banner (and its trailing newline) so we
    can prepend a fresh one each cycle without stacking."""
    if not text or not text.startswith(COMMENT_MARKER):
        return text
    end = text.find("-->", len(COMMENT_MARKER))
    if end == -1:
        return text  # malformed; leave alone
    rest_start = end + len("-->")
    if rest_start < len(text) and text[rest_start] == "\n":
        rest_start += 1
    return text[rest_start:]


def _fetch_export_xml(site, title: str) -> str | None:
    """Fetch the canonical Special:Export XML for a page (full history).

    Returns None if the export response lacks a <page> block (i.e. it's
    just siteinfo — the page didn't exist, or Miraheze returned a dud).
    The earlier implementation returned such responses anyway, which
    caused the orchestrator to commit siteinfo-only "placeholder" files
    into the archive repo. Those placeholders then blocked retries via
    archive_exists(). Reject them here instead.
    """
    host = site.host
    path = site.path
    url = f"https://{host}{path}index.php?title=Special:Export&action=submit"
    # `curonly` MUST be omitted for full history — SpecialExport.php uses
    # getCheck() which treats any present value (even "0") as truthy.
    resp = site.connection.post(
        url,
        data={"pages": title, "history": "1", "wpDownload": "1"},
    )
    resp.raise_for_status()
    xml = resp.text
    if "<page>" not in xml:
        return None
    return xml


def _list_contributors(site, title: str, limit: int = 50) -> list[str]:
    """Unique usernames that edited this page, oldest first, deduped in order."""
    params = {
        "prop": "revisions",
        "titles": title,
        "rvprop": "user",
        "rvlimit": "max",
        "rvdir": "newer",
    }
    seen: list[str] = []
    cont = {}
    while True:
        q = dict(params)
        q.update(cont)
        result = site.api("query", **q)
        pages = result.get("query", {}).get("pages", {})
        for _, p in pages.items():
            for rev in p.get("revisions", []):
                u = rev.get("user")
                if u and not rev.get("userhidden") and u not in seen:
                    seen.append(u)
                    if len(seen) >= limit:
                        return seen
        if "continue" in result:
            cont = result["continue"]
        else:
            break
    return seen


def _revision_count_capped(site, title: str, cap: int = 2) -> int:
    """Returns up to `cap` revisions for the page, enough to distinguish
    'single revision' vs 'multi-revision' without fetching thousands."""
    result = site.api(
        "query", prop="revisions", titles=title, rvprop="ids", rvlimit=cap,
    )
    for _, p in result.get("query", {}).get("pages", {}).items():
        return len(p.get("revisions", []))
    return 0


def run(site, page, run_tag: str, apply: bool) -> tuple[bool, str]:
    """
    Heavy-op entry point. Returns (page_was_modified, status_message).
    If page_was_modified, orchestrator refetches text before downstream ops.
    """
    if os.getenv("ENABLE_HISTORY_OFFLOAD") != "1":
        return False, "history_offload disabled (set ENABLE_HISTORY_OFFLOAD=1 to enable)"

    # Use the full title (with namespace prefix); the archive repo shards
    # files by namespace folder to avoid collisions between e.g. mainspace
    # "Foo" and "Category:Foo", which would otherwise share a slug.
    title = page.name
    ns = page.namespace
    enable_destructive = os.getenv("ENABLE_REVDEL") == "1"
    enable_fandom_mirror = os.getenv("ENABLE_FANDOM_MIRROR") == "1"

    try:
        current_text = page.text()
    except Exception as e:
        return False, f"could not read page: {e}"

    if _REDIRECT_RE.search(current_text):
        return False, "skipped: page is a redirect"

    # Fast-path skip: already in offloaded steady state.
    try:
        rev_count = _revision_count_capped(site, title)
    except Exception as e:
        return False, f"could not count revisions: {e}"
    if rev_count <= 1 and current_text.startswith(COMMENT_MARKER):
        return False, "already offloaded (banner + single revision)"
    if rev_count <= 1:
        return False, "no history to offload (single revision)"

    # Stage 0: Fandom mirror. Runs BEFORE any destructive source-side work
    # so we only delete pages that are known preserved on fandom.
    if enable_fandom_mirror and apply:
        ok, msg = fandom_mirror.mirror_page(site, title, run_tag)
        if not ok:
            return False, f"fandom mirror FAILED ({msg}); aborting offload"
        print(f"  fandom mirror: {msg}")

    # Stage 1: XML archive (idempotent — skip if already present).
    # Refuse to archive a placeholder: if Special:Export returned siteinfo
    # only with no <page> block, don't commit — let the next run retry.
    if not _archive_repo.archive_exists(title, ns):
        if not apply:
            return False, "DRY RUN: would mirror + archive + delete + recreate"
        xml_text = _fetch_export_xml(site, title)
        if xml_text is None:
            return False, "Special:Export returned no <page> block; skipping offload"
        _archive_repo.write_and_commit(title, xml_text, run_tag, ns)

    if not apply:
        return False, "DRY RUN: would delete + recreate"

    if not enable_destructive:
        return False, "archive+mirror done; delete+recreate skipped (ENABLE_REVDEL not set)"

    # Compute the recreate payload BEFORE deletion so we don't lose content
    # if delete succeeds but we then fail computing the new text.
    body = _strip_existing_banner(current_text)
    contributors = _list_contributors(site, title)
    new_text = _top_comment(title, run_tag) + "\n" + body
    summary = _build_summary(title, contributors, run_tag)

    # Stage 2: Delete. Moves all revisions into the per-title deleted-edits
    # pool (accessible via Special:Undelete). Requires the `delete` right —
    # EmmaBot has sysop on shintowiki so this is satisfied.
    delete_reason = (
        "History offloaded to XML archive and mirrored to shinto.fandom.com. "
        "Full history recoverable via Special:Undelete."
    )
    try:
        page.delete(reason=delete_reason)
    except Exception as e:
        return False, f"page delete failed: {e}"

    # Stage 3: Recreate with banner + current content. Refetch the Page
    # object so mwclient isn't working against stale post-delete state.
    fresh_page = site.pages[title]
    try:
        fresh_page.save(new_text, summary=summary)
    except Exception as e:
        return False, (
            f"recreate FAILED after delete succeeded: {e}. "
            f"Page is currently deleted; manual Special:Undelete needed."
        )

    return True, f"offloaded; deleted {rev_count}+ revs and recreated with banner"
