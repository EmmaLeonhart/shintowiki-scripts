"""
categories_to_bottom op
========================
Moves stray ``[[Category:...]]`` tags on their own line to the end of
the page, preserving their original order. A category is "stray" if it
appears before non-category content elsewhere on the page — i.e. there
is substantive text after it that isn't part of the page's trailing
category block.

Namespace coverage:
  * Mainspace (0) and the other subject-side wikitext namespaces:
    User, Project, File, Help.
  * Talk-side wikitext namespaces (odd-numbered).
Excluded:
  * Template (10) — handled by ``noinclude_wrap``, which keeps cats
    inside ``<noinclude>`` rather than just at the bottom.
  * Category (14) — handled by ``normalize_category_page``, which
    rebuilds the page into a canonical templates/interwikis/categories
    structure that already terminates with the category links.
  * MediaWiki (8) — system messages are intentionally untouched by
    every orchestrator op.
  * Non-wikitext namespaces (420/828/860/862 GeoJson/Module/Item/
    Property) — no wikitext to parse.

Matches only categories that occupy their own line. Inline cats inside
a sentence, a ref tag, a template parameter, or a gallery block are
left untouched: the cleanup is high-value for own-line cats imported
from enwiki/jawiki that ended up in the middle of the wikitext, and
low-value/dangerous for inline ones whose surrounding context matters.

Redirects are skipped — appending content after a ``#REDIRECT`` line
breaks the redirect.
"""

import re

from ..common import REDIRECT_RE

NAME = "categories_to_bottom"
NAMESPACES = (
    0,                             # main
    1, 3, 5, 7, 11, 13, 15,        # subject + talk pairs (excl. 8 MediaWiki, 9 MediaWiki talk)
    2, 4, 6, 12,                   # User, Project, File, Help (subject side)
    421, 829, 861, 863,            # GeoJson/Module/Item/Property talk
)

# A category tag occupying its own line. Captures:
#   - optional leading whitespace (consumed but not in the captured group)
#   - the cat tag itself (group 1)
#   - optional trailing whitespace
#   - a terminating newline OR end-of-string
# `^` and `\n|\Z` together pin the match to a full line. Inline cats
# (`Some text [[Category:Foo]] more text`) are deliberately not matched.
_CATEGORY_LINE_RE = re.compile(
    r"^[ \t]*(\[\[\s*Category\s*:[^\]\n|]+(?:\|[^\]\n]*)?\s*\]\])[ \t]*(?:\n|\Z)",
    re.IGNORECASE | re.MULTILINE,
)


def apply(title: str, text: str):
    if not text:
        return None, None
    if REDIRECT_RE.search(text):
        return None, None

    matches = list(_CATEGORY_LINE_RE.finditer(text))
    if not matches:
        return None, None

    # Walk matches from last to first. A match is part of the trailing
    # block if everything between its end and the next confirmed-trailing
    # match's start (or end of text for the very last match) is
    # whitespace-only. As soon as a match fails this test, every earlier
    # match is stray by definition.
    trailing_idx: set[int] = set()
    next_start = len(text)
    for i in reversed(range(len(matches))):
        m = matches[i]
        between = text[m.end():next_start]
        if between.strip() == "":
            trailing_idx.add(i)
            next_start = m.start()
        else:
            break

    stray = [m for i, m in enumerate(matches) if i not in trailing_idx]
    if not stray:
        return None, None

    # Remove stray cat lines from their positions, right-to-left so
    # offsets stay valid.
    new_text = text
    for m in reversed(stray):
        new_text = new_text[:m.start()] + new_text[m.end():]

    # Collapse runs of 3+ newlines the removals may have created, and
    # drop any leading newlines if the removed cat was on the first line.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    new_text = new_text.lstrip("\n")

    # Append stray cats at the bottom, preserving original order.
    tags = [m.group(1) for m in stray]
    new_text = new_text.rstrip() + "\n" + "\n".join(tags) + "\n"

    if new_text == text:
        return None, None
    return new_text, f"move {len(stray)} stray category tag(s) to bottom of page"
