"""
history_offload op
===================
Archives the full revision history of a page to the XML archive repo, then
makes one "truncation" edit on the wiki that keeps only the current content
plus a top-of-page HTML comment pointing at the archive viewer. The prior
revisions are then hidden via RevisionDelete so they drop out of subsequent
XML exports — which is the whole point: reduce the wiki-farm export burden.

Safety:
  * Runs only when ENABLE_HISTORY_OFFLOAD=1 (env var). Otherwise the op is
    a no-op so it can safely sit at the top of every orchestrator OPS list.
  * Order is archive → commit → push → wiki edit → revision-delete. Each
    step is gated on the previous succeeding, so a crash leaves either a
    harmless archive file or, at worst, an extra truncation-notice edit on
    the page (history still intact, easy to revert).
  * Revision-delete runs only when ENABLE_REVDEL=1 (separate gate). Stage 1
    validates archives + truncation edits; stage 2 flips the revdel switch.
  * Cycles idempotently: on each re-visit the prior truncation banner is
    stripped and a fresh one (carrying the current run_tag) is prepended,
    producing a text-distinct new revision. Stage 3 then revdels every
    prior revision including any earlier truncation edits, so the page
    converges to a single visible revision: the most recent run's.

The op sets HANDLES_SAVE = True, which tells common.run_orchestrator to run
it in a pre-pass and then refetch page.text() before the regular apply()
ops see the page. That way downstream per-page ops act on the truncated
version.

Why revision-delete rather than page-delete + recreate:
  * Preserves the page ID. Some downstream consumers (and the MediaWiki
    link table) treat page IDs as stable identifiers.
  * Preserves the link table — page-delete clears and reinserts every
    incoming link, which is expensive and touches every linker's cache.
  * Revision-delete hides content/user/comment; those revisions then drop
    out of standard XML exports, which is the wiki-farm-stability goal.
"""

import os
import urllib.parse

from . import _archive_repo, fandom_mirror

NAME = "history_offload"
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


def _fetch_export_xml(site, title: str) -> str:
    """Fetch the canonical Special:Export XML for a page (full history)."""
    host = site.host
    path = site.path
    url = f"https://{host}{path}index.php?title=Special:Export&action=submit"
    resp = site.connection.post(
        url,
        data={"pages": title, "curonly": "0", "wpDownload": "1"},
    )
    resp.raise_for_status()
    return resp.text


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


def _list_old_revids(site, title: str, keep_revid: int) -> list[int]:
    """Every revision of the page except keep_revid."""
    params = {
        "prop": "revisions",
        "titles": title,
        "rvprop": "ids",
        "rvlimit": "max",
    }
    revids: list[int] = []
    cont = {}
    while True:
        q = dict(params)
        q.update(cont)
        result = site.api("query", **q)
        pages = result.get("query", {}).get("pages", {})
        for _, p in pages.items():
            for rev in p.get("revisions", []):
                rid = rev.get("revid")
                if rid and rid != keep_revid:
                    revids.append(rid)
        if "continue" in result:
            cont = result["continue"]
        else:
            break
    return revids


def _revdel(site, title: str, revids: list[int]) -> tuple[int, list[str]]:
    """Hide content+comment+user on the given revision IDs. Needs deleterevision
    right (EmmaBot has sysop on shintowiki, so this is satisfied).

    Returns (number of revisions successfully hidden, list of error strings).
    Errors are COLLECTED and returned rather than raised, so one bad batch
    doesn't abort the rest of the page's offload; the caller logs them.
    """
    if not revids:
        return 0, []
    token = site.get_token("csrf")
    done = 0
    errors: list[str] = []
    # action=revisiondelete accepts up to 50 ids per call. It is a WRITE
    # action and must go over POST — some mwclient versions default api()
    # to GET, which silently yields an empty response and leaves revisions
    # visible. Force http_method='POST' explicitly.
    for i in range(0, len(revids), 50):
        batch = revids[i : i + 50]
        try:
            resp = site.api(
                "revisiondelete",
                http_method="POST",
                type="revision",
                target=title,
                ids="|".join(str(r) for r in batch),
                hide="content|comment|user",
                reason="History offloaded to XML archive; see top-of-page comment for link.",
                token=token,
            )
        except Exception as e:
            errors.append(f"batch starting {batch[0]}: {e}")
            continue
        # The API returns {"revisiondelete": {"status": "Success", "items": [...]}}
        # on success. Count items whose status reflects a hide (errored items
        # come back with "errors"). Be defensive about shape — treat a
        # non-"Success" top-level status as an error.
        rd = (resp or {}).get("revisiondelete") or {}
        status = rd.get("status")
        items = rd.get("items") or []
        if status != "Success":
            errors.append(f"batch starting {batch[0]}: API status={status!r} resp={resp!r}")
            continue
        for item in items:
            if item.get("errors"):
                errors.append(f"rev {item.get('id')}: {item['errors']}")
            else:
                done += 1
    return done, errors


def run(site, page, run_tag: str, apply: bool) -> tuple[bool, str]:
    """
    Heavy-op entry point. Returns (page_was_modified, status_message).
    If page_was_modified, orchestrator refetches text before downstream ops.
    """
    if os.getenv("ENABLE_HISTORY_OFFLOAD") != "1":
        return False, "history_offload disabled (set ENABLE_HISTORY_OFFLOAD=1 to enable)"

    title = page.page_title if hasattr(page, "page_title") else page.name
    enable_revdel = os.getenv("ENABLE_REVDEL") == "1"
    enable_fandom_mirror = os.getenv("ENABLE_FANDOM_MIRROR") == "1"

    try:
        current_text = page.text()
    except Exception as e:
        return False, f"could not read page: {e}"

    # Stage 0: Fandom mirror. Runs BEFORE truncation/revdel so the
    # destructive source-side edits only happen if the fandom copy is
    # known good. A failed mirror aborts the op for this page — the
    # wiki is left untouched, retaining full history for manual followup.
    # (The XML archive in stage 1 is always safe and independent.)
    if enable_fandom_mirror and apply:
        ok, msg = fandom_mirror.mirror_page(site, title, run_tag)
        if not ok:
            return False, f"fandom mirror FAILED ({msg}); aborting offload"
        print(f"  fandom mirror: {msg}")

    # Stage 1: XML archive (idempotent — skip if already present).
    if not _archive_repo.archive_exists(title):
        if not apply:
            return False, "DRY RUN: would mirror to fandom + archive + edit + revdel"
        xml_text = _fetch_export_xml(site, title)
        _archive_repo.write_and_commit(title, xml_text, run_tag)

    if not apply:
        return False, "DRY RUN: would refresh banner + edit + revdel"

    # Stage 2: Truncation edit. Strip any prior banner so we don't stack,
    # then prepend a fresh one. The banner AND the summary embed run_tag,
    # so each cycle produces a text-distinct revision — MediaWiki can't
    # suppress as a null edit, and the newest revid rotates forward. The
    # revdel in stage 3 then hides every prior revision (including prior
    # truncation edits), converging each page to one visible revision:
    # the most recent run's truncation.
    body = _strip_existing_banner(current_text)
    contributors = _list_contributors(site, title)
    new_text = _top_comment(title, run_tag) + "\n" + body
    summary = _build_summary(title, contributors, run_tag)
    page.save(new_text, summary=summary)

    # Stage 3: RevDel the rest. Gated separately so stage-1 rollout is reversible.
    if enable_revdel:
        # page.revisions() hits the API fresh each call — no need to reload().
        # (mwclient's Page has no .reload(); calling it raised AttributeError
        # and skipped revdel on every page.)
        try:
            keep_revid = next(iter(page.revisions(limit=1)))["revid"]
        except StopIteration:
            return True, "saved truncation edit; could not list revisions for revdel"
        olds = _list_old_revids(site, title, keep_revid)
        done, errors = _revdel(site, title, olds)
        if errors:
            # Surface WHICH batches failed so a silent-revdel regression
            # doesn't get masked by the orchestrator's generic heavy-op
            # error handler. Return True (page was still modified by the
            # truncation edit) but make the message carry the failure.
            err_summary = "; ".join(errors[:3])
            if len(errors) > 3:
                err_summary += f" (+{len(errors) - 3} more)"
            return True, (
                f"offloaded; archived + truncated + revdel'd {done}/{len(olds)} revs "
                f"(errors: {err_summary})"
            )
        return True, f"offloaded; archived + truncated + revdel'd {done}/{len(olds)} revs"

    return True, "offloaded; archived + truncated (revdel disabled)"
