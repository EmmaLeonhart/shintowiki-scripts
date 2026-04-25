"""
strip_html_comments op
======================
Removes HTML comments (``<!-- ... -->``) from wikitext pages. Imported
pages accumulate cruft — section markers from the import script
(``<!--enwiki derived wikidata interwikis-->``), duplicated-content
sentinels, dead descriptive notes — that don't render but bloat the
source and clutter the fandom mirror copy.

Preserves the ``<!-- History offloaded: ... -->`` banner verbatim.
``history_offload``'s steady-state detection looks for that exact
prefix; stripping it would force a re-offload on every cycle.

Marked ``PRE_HEAVY = True`` so the orchestrator runs it before any
heavy op. That way ``history_offload``'s fandom mirror and XML archive
capture the cleaned text, and the recreated page revision is also
clean — instead of having to wait for a second cycle to propagate the
cleanup.
"""

import re

NAME = "strip_html_comments"

# Wikitext namespaces only. Non-wikitext content (Module Lua, GeoJson,
# Wikibase JSON — ns 420/828/860/862) doesn't use HTML comments and
# stripping ``<!-- -->`` from JSON would be wrong.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)

PRE_HEAVY = True

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Marker that history_offload uses to detect the steady state.
HISTORY_BANNER_PREFIX = "<!-- History offloaded:"


def apply(title: str, text: str):
    if not text:
        return None, None

    from ..common import REDIRECT_RE
    if REDIRECT_RE.search(text):
        return None, None

    def _replace(match: "re.Match[str]") -> str:
        if match.group(0).startswith(HISTORY_BANNER_PREFIX):
            return match.group(0)
        return ""

    new_text = COMMENT_RE.sub(_replace, text)
    if new_text == text:
        return None, None

    # Collapse runs of 3+ newlines the removal may have created.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    if new_text == text:
        return None, None

    return new_text, "strip HTML comments"
