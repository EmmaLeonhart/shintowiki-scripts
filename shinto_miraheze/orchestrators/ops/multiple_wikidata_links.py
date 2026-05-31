"""
multiple_wikidata_links op
==========================
Detector + tagger for backlog item 6 ("Multiple {{wikidata link}} on one
page"). A page should carry exactly one ``{{wikidata link}}`` template; two
or more usually means a Wikidata disambiguation issue that needs per-case
human review.

Pure-text, self-healing: when the page has 2+ ``{{wikidata link…}}`` calls it
gains ``[[Category:Pages with multiple wikidata links]]``; when it drops back
to 0/1 the tag is stripped again. The dashboard's backlog page reads this
category, so the list maintains itself as the orchestrator sweeps.

Mainspace + Category namespaces — the same namespaces ``wikidata_link`` runs
in (ns 10 templates carry the call inside <noinclude> and shouldn't be
flagged). Redirects are skipped. Runs AFTER ``wikidata_link`` in the OPS list
so it sees the final template count (wikidata_link only ever appends a blank
template to pages that have NONE, so it can't manufacture a second one).
"""

import re

from ..common import REDIRECT_RE

NAME = "multiple_wikidata_links"
NAMESPACES = (0, 14)

CATEGORY = "Pages with multiple wikidata links"
CATEGORY_TAG = f"[[Category:{CATEGORY}]]"

# Counts both "{{wikidata link|…}}" and a blank "{{wikidata link}}" — the
# trailing [|}] disambiguates the template name from longer names.
WD_LINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*[|}]", re.IGNORECASE)

CATEGORY_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages with multiple wikidata links\s*\]\]\n?",
    re.IGNORECASE,
)


def apply(title: str, text: str):
    if REDIRECT_RE.search(text):
        return None, None

    count = len(WD_LINK_RE.findall(text))
    has_tag = bool(CATEGORY_RE.search(text))
    wants_tag = count >= 2

    if has_tag == wants_tag:
        return None, None

    if wants_tag:
        new_text = text.rstrip() + "\n" + CATEGORY_TAG + "\n"
        return new_text, f"tag [[:Category:{CATEGORY}]] ({count} wikidata-link templates)"

    new_text = CATEGORY_RE.sub("", text)
    if new_text == text:
        return None, None
    return new_text, f"strip [[:Category:{CATEGORY}]] (now {count} wikidata-link template(s))"
