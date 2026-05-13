"""
strip_afc_templates op
======================
Removes ``{{AfC submission}}`` and ``{{AfC topic}}`` template calls
from mainspace pages. These are enwiki Articles-for-Creation review
templates — they're meaningful on enwiki where AfC is a workflow, but
they get carried in on enwiki imports and have no meaning here. Once
in the wiki they render as red-template warnings, clutter
category-style hatnotes at the top of imported articles, and
occasionally trip up other ops that don't expect them.

Mainspace-only. The templates can take arbitrary parameter strings
(timestamp, user, ns code, etc. — see
``duplicated_content/Kōtai Jingū.wiki`` for a real example) so the op
brace-walks each match instead of using a non-greedy regex that would
break on nested templates inside parameter values.
"""

import re

NAME = "strip_afc_templates"
NAMESPACES = (0,)

# Anchors the open of an AfC template. We brace-walk forward from each
# match to find the matching ``}}`` so nested templates inside
# parameter values don't trip us up.
_AFC_OPEN_RE = re.compile(r"\{\{\s*AfC\s+(?:submission|topic)\b", re.IGNORECASE)


def _strip_one(text: str, start: int) -> tuple[str, int] | None:
    """Return (new_text, position-after-removal) if a balanced template
    can be parsed starting at ``text[start:start+2] == "{{"``; otherwise
    None to signal the open was malformed."""
    depth = 0
    i = start
    n = len(text)
    while i < n - 1:
        pair = text[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
        elif pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                # Also swallow a trailing newline so we don't leave a
                # blank line where the template used to be.
                end = i
                if end < n and text[end] == "\n":
                    end += 1
                return text[:start] + text[end:], start
        else:
            i += 1
    return None  # unbalanced — leave the page alone


def apply(title: str, text: str):
    if "{{" not in text:
        return None, None
    new_text = text
    removed = 0
    while True:
        m = _AFC_OPEN_RE.search(new_text)
        if not m:
            break
        result = _strip_one(new_text, m.start())
        if result is None:
            break
        new_text, _ = result
        removed += 1

    if removed == 0 or new_text == text:
        return None, None

    # Collapse runs of 3+ newlines created by the removal.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    new_text = new_text.lstrip("\n")
    return new_text, f"strip {removed} AfC template(s)"
