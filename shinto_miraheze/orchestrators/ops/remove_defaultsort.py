"""
remove_defaultsort op
======================
Strips leftover ``{{DEFAULTSORT:...}}`` magic-word invocations from
mainspace pages. They were inherited from the enwiki/jawiki imports
and have no semantic value on shintowiki — categories here use direct
sort keys where ordering matters, and DEFAULTSORT would silently
override them otherwise.

Mainspace-only because:
  * Templates never carry DEFAULTSORT.
  * Category pages occasionally use it deliberately to set the sort
    order of the category itself in a parent category, which we want
    to preserve.

Implemented as a cyclical per-page op rather than a one-shot script:
re-imports from enwiki/jawiki can re-introduce DEFAULTSORT, so the
removal needs to keep running over time — not just once.
"""

import re

NAME = "remove_defaultsort"
NAMESPACES = (0,)

# Matches {{DEFAULTSORT:...}} with optional surrounding whitespace and
# an optional trailing newline so removal collapses the whole line. Case
# insensitive because the magic word accepts DEFAULTSORT / defaultsort.
# `[^{}\n]*` keeps the match line-scoped — we refuse to span across
# nested templates, which DEFAULTSORT never does in real wikitext.
DEFAULTSORT_RE = re.compile(
    r"[ \t]*\{\{\s*DEFAULTSORT\s*:[^{}\n]*\}\}[ \t]*\n?",
    re.IGNORECASE,
)


def apply(title: str, text: str):
    new_text, n = DEFAULTSORT_RE.subn("", text)
    if n == 0 or new_text == text:
        return None, None
    return new_text, f"remove {n} DEFAULTSORT invocation(s) (leftover from imports)"
