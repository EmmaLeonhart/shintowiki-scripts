"""
strip_char_count_cats op
=========================
Removes stale ``[[Category:Pages with N+ untranslated japanese characters]]``
tags from pages that have since been marked ``[[Category:Translated pages]]``.
Ported from the standalone ``strip_translated_char_count_cats.py`` so the
orchestrator's page-walk handles iteration and state, eliminating a duplicate
loop across mainspace.

Acts only if the page is in Category:Translated pages — a char-count tag on
an un-translated page is correct, not stale.

Thresholds kept in sync with ``tag_untranslated_japanese.py`` / the
``untranslated_japanese`` op.
"""

import re

NAME = "strip_char_count_cats"
NAMESPACES = (0,)

THRESHOLDS = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]
_THRESHOLD_ALT = "|".join(str(t) for t in THRESHOLDS)

CHAR_COUNT_CAT_RE = re.compile(
    rf"[ \t]*\[\[\s*Category\s*:\s*Pages with (?:{_THRESHOLD_ALT})\+ untranslated japanese characters\s*\]\][ \t]*\n?",
    re.IGNORECASE,
)
TRANSLATED_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Translated pages\s*\]\]",
    re.IGNORECASE,
)


def apply(title: str, text: str):
    if not text:
        return None, None
    if not TRANSLATED_CAT_RE.search(text):
        return None, None
    new_text, n = CHAR_COUNT_CAT_RE.subn("", text)
    if n == 0 or new_text == text:
        return None, None
    return new_text, f"remove {n} stale untranslated-japanese char-count tag(s)"
