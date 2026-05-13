"""
strip_self_categorization op
============================
Removes self-categorization from category pages: when ``Category:Foo``
contains ``[[Category:Foo]]`` in its own wikitext, the category becomes
its own member. That keeps the category from ever appearing "empty"
to the unused-categories sweep, so it never reaches
``delete_unused_categories``. Per the queue plan, that's the main
mechanism currently blocking the categories backlog from draining.

Category-namespace only. We match the page's own title (which the
orchestrator passes in) against every ``[[Category:...]]`` reference in
the text. Matching is case-insensitive on the first char (MediaWiki
folds the leading char of a title) and tolerates extra whitespace
inside the brackets.

Sort-key suffixes are supported: ``[[Category:Foo|sortkey]]`` is also
a self-categorization and is also stripped.
"""

import re

NAME = "strip_self_categorization"
NAMESPACES = (14,)


def _normalize(name: str) -> str:
    """Normalize a category-name for comparison: trim, collapse internal
    whitespace runs to single spaces, lowercase the first character.

    MediaWiki's title canonicalization is more aggressive than this in
    pathological cases (underscore/space equivalence, unicode
    normalization forms) but for the strip-self-categorization purpose
    a simple comparison covers the cases that actually appear: trailing
    sortkeys, slight whitespace variations, and first-char case
    differences. False negatives (we miss a self-cat) just leave the
    page untouched, which is safe; false positives (we strip a
    legitimate category) would be the bad outcome and would require a
    very contrived collision to occur.
    """
    name = re.sub(r"\s+", " ", name.strip())
    if name:
        name = name[0].upper() + name[1:]
    return name


def apply(title: str, text: str):
    if not title.startswith("Category:"):
        return None, None
    own_name = _normalize(title[len("Category:"):])
    if not own_name:
        return None, None

    # Match every [[Category:...]] reference, optionally with a sortkey.
    # We compute the replacement in two passes: count what we'd strip,
    # then commit. Newline-trailing is consumed so the strip doesn't
    # leave a blank line behind.
    pattern = re.compile(
        r"\[\[\s*Category\s*:\s*([^\]|]+?)\s*(?:\|[^\]]*)?\s*\]\]\n?",
        re.IGNORECASE,
    )

    removed = 0

    def _replace(match: "re.Match[str]") -> str:
        nonlocal removed
        cat_name = _normalize(match.group(1))
        if cat_name == own_name:
            removed += 1
            return ""
        return match.group(0)

    new_text = pattern.sub(_replace, text)
    if removed == 0 or new_text == text:
        return None, None

    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    return new_text, f"strip {removed} self-categorization(s)"
