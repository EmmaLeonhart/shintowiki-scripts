"""
strip_html_comments op
======================
Removes HTML comments (``<!-- ... -->``) from wikitext pages. The
**primary target** is the multi-kilobyte ``<!-- History offloaded: ...
-->`` banner that ``history_offload`` prepended to every offloaded page
— a banner pointing at the GitHub XML archive and the fandom mirror,
with run-tag links that lose meaning as soon as the GitHub Actions run
expires. Those banners are the most destructive comment cruft on the
wiki: they actively break pages, especially in MediaWiki (ns=8) and
Template (ns=10) namespaces where stray HTML comments can corrupt
rendering or parser-function evaluation. Cleaning them up is what this
op exists for. Other HTML-comment cruft (import-script section markers
like ``<!--enwiki derived wikidata interwikis-->``, duplicated-content
sentinels, dead descriptive notes) is also stripped.

Banner stripping is unconditional everywhere **except** in Category
namespace. In ``DESTRUCTIVE_NAMESPACES`` (currently ``{14}`` — see
``history_offload``) the offload op deletes and recreates the page on
every offload cycle, re-prepending a fresh banner; stripping there
forces an oscillating delete+recreate every cycle and discards
revisions repeatedly. So for category pages, the banner is preserved
until ``history_offload`` retires (past its ``CUTOFF_DATE`` or with
``ENABLE_HISTORY_OFFLOAD != "1"``). Everywhere else, the banner is
stripped immediately — ``history_offload`` won't re-add it because its
Stage 3 (recreate) is gated on ``DESTRUCTIVE_NAMESPACES``; Stage 0
(fandom mirror) and Stage 1 (XML archive) keep running as idempotent
no-ops, which the user explicitly wants for ns=8 MediaWiki.

Marked ``PRE_HEAVY = True`` so the orchestrator runs it before any
heavy op. That way ``history_offload``'s fandom mirror and XML archive
capture the cleaned text, and the recreated page revision is also
clean — instead of having to wait for a second cycle to propagate the
cleanup.

Scope note: ``NAMESPACES`` includes ns=8 MediaWiki explicitly, even
though CLAUDE.md says ns=8 is excluded from every orchestrator. The
exclusion was about generic space-saving ops being too risky on
interface messages; this op exists specifically to undo damage that
offload caused in ns=8, so it's an explicit carve-out. No orchestrator
currently walks ns=8 — the companion one-shot
``archive/strip_mediawiki_banners.py`` did that walk and applied this
op (archived 2026-05-27 — its one-shot job is done; ns=8 is no longer
being damaged because ``history_offload`` is excluded from every
orchestrator).
"""

import datetime
import os
import re

NAME = "strip_html_comments"

# Wikitext namespaces only. Non-wikitext content (Module Lua, GeoJson,
# Wikibase JSON — ns 420/828/860/862) doesn't use HTML comments and
# stripping ``<!-- -->`` from JSON would be wrong. ns=8 MediaWiki IS
# included here as an explicit carve-out (see docstring) even though
# no recurring orchestrator walks it.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)

PRE_HEAVY = True

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Marker that history_offload uses to detect the steady state.
HISTORY_BANNER_PREFIX = "<!-- History offloaded:"
# Title prefix for the one namespace where history_offload still does
# destructive delete+recreate. Preserving banners here avoids oscillation
# with that op while it's still active.
CATEGORY_TITLE_PREFIX = "Category:"


def _history_offload_retired() -> bool:
    """True when ``history_offload`` will no longer re-prepend the banner.

    Mirrors the disable-gate in ``history_offload.run()``: the op is
    retired if its enable flag is off, or if today is past its cutoff
    date without the force-override.
    """
    if os.getenv("ENABLE_HISTORY_OFFLOAD") != "1":
        return True
    if os.getenv("FORCE_HISTORY_OFFLOAD_PAST_CUTOFF") == "1":
        return False
    from . import history_offload
    return datetime.datetime.utcnow().date() >= history_offload.CUTOFF_DATE


def apply(title: str, text: str):
    if not text:
        return None, None

    from ..common import REDIRECT_RE
    if REDIRECT_RE.search(text):
        return None, None

    # Preserve the banner ONLY in category namespace while history_offload
    # is still actively recreating category pages. Everywhere else
    # (mainspace, MediaWiki, Template, Help, etc.) the banner is bloat
    # that breaks rendering and we strip it now.
    preserve_banner = (
        title.startswith(CATEGORY_TITLE_PREFIX)
        and not _history_offload_retired()
    )

    def _replace(match: "re.Match[str]") -> str:
        if preserve_banner and match.group(0).startswith(HISTORY_BANNER_PREFIX):
            return match.group(0)
        return ""

    new_text = COMMENT_RE.sub(_replace, text)
    if new_text == text:
        return None, None

    # Collapse runs of 3+ newlines the removal may have created, and
    # trim a leading newline left behind when the banner was the first
    # line on the page.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    new_text = new_text.lstrip("\n")
    if new_text == text:
        return None, None

    return new_text, "strip HTML comments"
