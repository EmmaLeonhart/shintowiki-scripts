"""
wikidata_link op
================
Tags pages missing a {{wikidata link|...}} template with
[[Category:Pages without wikidata]]. Applies to mainspace, category, and
template namespaces.

Ported from tag_pages_without_wikidata.py so the orchestrators can call it
per-page. The original script remains in place for now; once the three
orchestrators are wired into CI, it can be retired.

Skips redirects: they never carry {{wikidata link}} directly, so tagging
them would flood [[Category:Pages without wikidata]] with thousands of
QID-slug redirects that have nothing actionable to fix — the target page
is what needs the wikidata link.
"""

import re

from ..common import REDIRECT_RE

NAME = "wikidata_link"
NAMESPACES = (0, 10, 14)

TARGET_CAT = "Pages without wikidata"
CAT_TAG = f"[[Category:{TARGET_CAT}]]"

WD_LINK_RE = re.compile(r"\{\{wikidata link\|", re.IGNORECASE)
TARGET_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages without wikidata\s*\]\]",
    re.IGNORECASE,
)


def apply(title: str, text: str):
    if REDIRECT_RE.search(text):
        return None, None
    if WD_LINK_RE.search(text):
        return None, None
    if TARGET_CAT_RE.search(text):
        return None, None
    new_text = text.rstrip() + "\n" + CAT_TAG + "\n"
    return new_text, "tag page without wikidata link"
