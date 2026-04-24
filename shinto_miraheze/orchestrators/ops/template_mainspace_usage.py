"""
template_mainspace_usage op
============================
For each visited template page, queries the MediaWiki API to see
whether the template is transcluded on any mainspace (ns=0) page, and
maintains exactly one of two complementary maintenance categories
inside the template's ``<noinclude>`` block:

  * at least one mainspace transclusion →
    ``[[Category:Templates transcluded in mainspace]]``
  * zero mainspace transclusions →
    ``[[Category:Templates not transcluded in mainspace]]``

The two categories partition the template namespace so they can be
filtered against each other. This gives us a way to surface templates
that were accidentally imported (e.g. via the wanted-templates import
pipeline) but are not actually used on any mainspace page — candidates
for deletion or review.

The category lives in ``<noinclude>`` so it only applies to the
template page itself, not to pages that transclude the template.

Heavy op (``HANDLES_SAVE = True``) because the decision requires a live
API query — ``prop=transcludedin&tinamespace=0&tilimit=1`` — which is
enough to cheaply distinguish "zero mainspace uses" from "at least one".

Env gate: ``ENABLE_TEMPLATE_USAGE_CHECK=1``. Left off by default so the
op can sit in the template orchestrator's OPS list without acting until
explicitly enabled via workflow input.
"""

import os
import re
import time

NAME = "template_mainspace_usage"
NAMESPACES = (10,)
HANDLES_SAVE = True

THROTTLE = 2.5

CAT_USED = "Templates transcluded in mainspace"
CAT_UNUSED = "Templates not transcluded in mainspace"
TAG_USED = f"[[Category:{CAT_USED}]]"
TAG_UNUSED = f"[[Category:{CAT_UNUSED}]]"

_CAT_USED_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Templates[ _]transcluded[ _]in[ _]mainspace\s*\]\]\n?",
    re.IGNORECASE,
)
_CAT_UNUSED_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Templates[ _]not[ _]transcluded[ _]in[ _]mainspace\s*\]\]\n?",
    re.IGNORECASE,
)

_NOINCLUDE_BLOCK_RE = re.compile(
    r"<noinclude\s*>(?P<body>.*?)</noinclude\s*>",
    re.IGNORECASE | re.DOTALL,
)


def _has_mainspace_transclusion(site, title: str) -> bool:
    """True if the template is transcluded on at least one ns=0 page.

    Uses ``tilimit=1`` so the query returns as soon as the first hit is
    found — we don't need a full list, just a boolean.
    """
    result = site.api(
        "query",
        prop="transcludedin",
        titles=title,
        tinamespace=0,
        tilimit=1,
    )
    pages = result.get("query", {}).get("pages", {})
    for _, p in pages.items():
        if p.get("transcludedin"):
            return True
    return False


def _insert_tag_in_noinclude(text: str, tag: str) -> str:
    """Insert ``tag`` inside an existing <noinclude> block, or append a
    new block containing it at the end of the page."""
    match = _NOINCLUDE_BLOCK_RE.search(text)
    if match:
        body = match.group("body")
        new_body = body.rstrip("\n") + f"\n{tag}\n"
        return text[: match.start("body")] + new_body + text[match.end("body") :]

    sep = "" if text.endswith("\n") else "\n"
    return f"{text}{sep}<noinclude>\n{tag}\n</noinclude>\n"


def run(site, page, run_tag: str, apply: bool) -> tuple[bool, str]:
    if os.getenv("ENABLE_TEMPLATE_USAGE_CHECK") != "1":
        return False, "template_mainspace_usage disabled (set ENABLE_TEMPLATE_USAGE_CHECK=1 to enable)"

    title = page.name

    try:
        current_text = page.text()
    except Exception as e:
        return False, f"could not read page: {e}"

    try:
        used_in_mainspace = _has_mainspace_transclusion(site, title)
    except Exception as e:
        return False, f"transcludedin query failed: {e}"

    has_used_tag = bool(_CAT_USED_RE.search(current_text))
    has_unused_tag = bool(_CAT_UNUSED_RE.search(current_text))

    # Compute the desired text: remove the wrong tag if present, add the
    # right tag if absent. We edit in one save to avoid double-writing.
    new_text = current_text
    actions: list[str] = []

    if used_in_mainspace:
        if has_unused_tag:
            new_text = _CAT_UNUSED_RE.sub("", new_text)
            actions.append(f"remove [[:Category:{CAT_UNUSED}]]")
        if not has_used_tag:
            new_text = _insert_tag_in_noinclude(new_text, TAG_USED)
            actions.append(f"add [[:Category:{CAT_USED}]]")
    else:
        if has_used_tag:
            new_text = _CAT_USED_RE.sub("", new_text)
            actions.append(f"remove [[:Category:{CAT_USED}]]")
        if not has_unused_tag:
            new_text = _insert_tag_in_noinclude(new_text, TAG_UNUSED)
            actions.append(f"add [[:Category:{CAT_UNUSED}]]")

    if not actions or new_text == current_text:
        return False, "already correctly categorized"

    summary_fragment = "; ".join(actions)
    if not apply:
        return False, f"DRY RUN: would {summary_fragment}"

    summary = f"Bot: {summary_fragment} {run_tag}"
    try:
        page.save(new_text, summary=summary)
    except Exception as e:
        return False, f"save failed: {e}"

    time.sleep(THROTTLE)
    return True, summary_fragment
