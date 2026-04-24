"""
wikidata_link op
================
Tags pages missing a {{wikidata link|...}} template with the appropriate
"missing wikidata" maintenance category:

* Mainspace / Category pages  → ``[[Category:Pages without wikidata]]``
  appended at the end of the page.
* Template pages              → ``[[Category:Templates missing wikidata]]``
  inserted inside a ``<noinclude>`` block so the category doesn't
  cascade through transclusion into every page that uses the template
  (which would drown the mainspace category with false positives).

Also strips the generic ``[[Category:Pages without wikidata]]`` tag from
template pages — older runs placed it at top level, which caused exactly
that cascade bug.

Skips redirects: they never carry {{wikidata link}} directly.
"""

import re

from ..common import REDIRECT_RE

NAME = "wikidata_link"
NAMESPACES = (0, 10, 14)

MAINSPACE_CAT = "Pages without wikidata"
TEMPLATE_CAT = "Templates missing wikidata"
MAINSPACE_TAG = f"[[Category:{MAINSPACE_CAT}]]"
TEMPLATE_TAG = f"[[Category:{TEMPLATE_CAT}]]"

WD_LINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|", re.IGNORECASE)

_MAINSPACE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages[ _]without[ _]wikidata\s*\]\]\n?",
    re.IGNORECASE,
)
_TEMPLATE_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Templates[ _]missing[ _]wikidata\s*\]\]\n?",
    re.IGNORECASE,
)
_NOINCLUDE_BLOCK_RE = re.compile(
    r"<noinclude\s*>(?P<body>.*?)</noinclude\s*>",
    re.IGNORECASE | re.DOTALL,
)


def _insert_in_noinclude(text: str, tag: str) -> str:
    """Insert `tag` inside the first existing <noinclude> block, or append
    a new block containing it at the end of the page."""
    match = _NOINCLUDE_BLOCK_RE.search(text)
    if match:
        body = match.group("body")
        new_body = body.rstrip("\n") + f"\n{tag}\n"
        return text[: match.start("body")] + new_body + text[match.end("body") :]
    sep = "" if text.endswith("\n") else "\n"
    return f"{text}{sep}<noinclude>\n{tag}\n</noinclude>\n"


def _apply_template(text: str):
    """Template-namespace variant. Keeps the maintenance tag inside
    <noinclude>, and migrates the old generic tag if present."""
    has_wd_link = bool(WD_LINK_RE.search(text))
    has_mainspace_tag = bool(_MAINSPACE_CAT_RE.search(text))
    has_template_tag = bool(_TEMPLATE_CAT_RE.search(text))

    new_text = text
    actions: list[str] = []

    # Always strip the mainspace tag from templates — on a template it
    # cascades through transclusion into every page using the template.
    if has_mainspace_tag:
        new_text = _MAINSPACE_CAT_RE.sub("", new_text)
        actions.append(f"strip stray [[:Category:{MAINSPACE_CAT}]]")

    if has_wd_link:
        # Template has a wikidata link → neither "missing" tag belongs.
        if has_template_tag:
            new_text = _TEMPLATE_CAT_RE.sub("", new_text)
            actions.append(f"strip [[:Category:{TEMPLATE_CAT}]] (wikidata link present)")
    else:
        # No wikidata link → ensure the template-specific tag is inside noinclude.
        if not has_template_tag:
            new_text = _insert_in_noinclude(new_text, TEMPLATE_TAG)
            actions.append(f"tag [[:Category:{TEMPLATE_CAT}]] inside <noinclude>")

    if not actions or new_text == text:
        return None, None
    return new_text, "; ".join(actions)


def apply(title: str, text: str):
    if REDIRECT_RE.search(text):
        return None, None

    if title.startswith("Template:"):
        return _apply_template(text)

    # Mainspace / Category: existing behaviour.
    if WD_LINK_RE.search(text):
        return None, None
    if _MAINSPACE_CAT_RE.search(text):
        return None, None
    new_text = text.rstrip() + "\n" + MAINSPACE_TAG + "\n"
    return new_text, "tag page without wikidata link"
