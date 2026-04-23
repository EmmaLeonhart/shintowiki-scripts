"""
remove_legacy_cat_templates op
===============================
Strips two legacy maintenance templates that were introduced by old
automated passes onto category pages and should not be there:

  * ``{{デフォルトソート:…}}`` — Japanese DEFAULTSORT artifact.
  * ``{{citation needed|…}}``  — sourcing tag; not appropriate on category pages.

Ported from ``shinto_miraheze/remove_legacy_cat_templates.py`` so the
category-orchestrator sweep handles iteration and state. The standalone
script was in wiki-cleanup's "Deprecated:" section with its own parallel
walk; the orchestrator covers the same ground via allpages(ns=14).
"""

import re

NAME = "remove_legacy_cat_templates"
NAMESPACES = (14,)

_STRIP_PATTERNS = [
    # {{デフォルトソート:SomeName}} — Japanese DEFAULTSORT artifact
    re.compile(r"\{\{\s*デフォルトソート\s*:[^\{\}]*\}\}\n?"),
    # {{citation needed}} / {{citation needed|date=…}} — sourcing tag artifact
    re.compile(r"\{\{\s*[Cc]itation\s+[Nn]eeded\s*(?:\|[^\{\}]*)?\}\}\n?"),
]


def apply(title: str, text: str):
    if not text:
        return None, None
    new_text = text
    for pat in _STRIP_PATTERNS:
        new_text = pat.sub("", new_text)
    if new_text.rstrip() == text.rstrip():
        return None, None
    return new_text, "remove legacy category-page templates ({{デフォルトソート}}, {{citation needed}})"
