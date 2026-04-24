"""
normalize_category_page op
===========================
Normalizes Category: pages to a strict structure keeping only
(1) templates, (2) interwiki links, (3) category links — in that order,
separated by ``<!--templates-->``, ``<!--interwikis-->``, ``<!--categories-->``
comment markers.

Ported from the standalone ``shinto_miraheze/normalize_category_pages.py``
so the category-orchestrator sweep handles iteration and state. The
standalone script was in wiki-cleanup's "Deprecated:" section with its
own parallel walk; the orchestrator covers the same ground via
allpages(ns=14).
"""

import re

from ..common import REDIRECT_RE

NAME = "normalize_category_page"
NAMESPACES = (14,)

CATEGORY_LINE_RE = re.compile(r"^\s*\[\[\s*Category\s*:[^\]]+\]\]\s*$", re.IGNORECASE)
INTERWIKI_LINE_RE = re.compile(r"^\s*\[\[\s*[a-z][a-z0-9-]{1,15}\s*:[^\]]+\]\]\s*$", re.IGNORECASE)

TEMPLATES_MARKER = "<!--templates-->"
INTERWIKIS_MARKER = "<!--interwikis-->"
CATEGORIES_MARKER = "<!--categories-->"


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _extract_top_level_templates(text: str) -> list[str]:
    templates = []
    depth = 0
    start = None
    i = 0
    while i < len(text):
        two = text[i:i + 2]
        if two == "{{":
            if depth == 0:
                start = i
            depth += 1
            i += 2
            continue
        if two == "}}" and depth > 0:
            depth -= 1
            i += 2
            if depth == 0 and start is not None:
                block = text[start:i].strip()
                if block:
                    templates.append(block)
                start = None
            continue
        i += 1
    return _dedupe_preserve_order(templates)


def _extract_interwikis_and_categories(text: str) -> tuple[list[str], list[str]]:
    interwikis = []
    categories = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if CATEGORY_LINE_RE.match(line):
            categories.append(line)
            continue
        if INTERWIKI_LINE_RE.match(line):
            # Skip local namespace-prefixed links like [[Category:...]] or
            # [[Template:...]] — only true language interwikis.
            lower = line.lower()
            if not (lower.startswith("[[category:") or lower.startswith("[[template:")):
                interwikis.append(line)
    return _dedupe_preserve_order(interwikis), _dedupe_preserve_order(categories)


def _build_normalized(text: str) -> str:
    templates = _extract_top_level_templates(text)
    interwikis, categories = _extract_interwikis_and_categories(text)
    lines = [TEMPLATES_MARKER, *templates, INTERWIKIS_MARKER, *interwikis, CATEGORIES_MARKER, *categories]
    return "\n".join(lines).rstrip() + "\n"


def apply(title: str, text: str):
    if not text:
        return None, None
    # Redirect category pages carry `#REDIRECT [[Category:…]]` or
    # `{{category redirect|…}}` — normalizing them would collapse the
    # page to empty marker comments and destroy the redirect.
    if REDIRECT_RE.search(text):
        return None, None
    new_text = _build_normalized(text)
    if new_text.rstrip() == text.rstrip():
        return None, None
    return new_text, "normalize category page structure (templates/interwikis/categories only)"
