"""
noinclude_wrap op
=================
Moves stray [[Category:...]] and {{wikidata link|...}} tags in templates
inside a trailing <noinclude> block. Template namespace only.

Ported from fix_template_noinclude.py.
"""

import re

NAME = "noinclude_wrap"
NAMESPACES = (10,)

FIXED_CAT = "Templates fixed with noinclude"
FIXED_CAT_TAG = f"[[Category:{FIXED_CAT}]]"

CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:[^\]]+\]\]", re.IGNORECASE)
WD_LINK_RE = re.compile(r"\{\{wikidata link\|[^}]*\}\}", re.IGNORECASE)


def _noinclude_regions(text: str):
    regions = []
    tag_open = re.compile(r"<noinclude\s*>", re.IGNORECASE)
    tag_close = re.compile(r"</noinclude\s*>", re.IGNORECASE)
    for m_open in tag_open.finditer(text):
        m_close = tag_close.search(text, m_open.end())
        end = m_close.end() if m_close else len(text)
        regions.append((m_open.start(), end))
    return regions


def _is_inside(pos: int, regions) -> bool:
    return any(start <= pos < end for start, end in regions)


def apply(title: str, text: str):
    regions = _noinclude_regions(text)
    stray = []

    for m in CATEGORY_RE.finditer(text):
        if _is_inside(m.start(), regions):
            continue
        if FIXED_CAT.lower() in m.group(0).lower():
            continue
        stray.append((m.start(), m.end(), m.group(0)))

    for m in WD_LINK_RE.finditer(text):
        if not _is_inside(m.start(), regions):
            stray.append((m.start(), m.end(), m.group(0)))

    if not stray:
        return None, None

    stray.sort(key=lambda x: x[0], reverse=True)
    tags_in_order = [tag for _, _, tag in reversed(stray)]

    new_text = text
    for start, end, _ in stray:
        if end < len(new_text) and new_text[end] == "\n":
            end += 1
        new_text = new_text[:start] + new_text[end:]
    while "\n\n\n" in new_text:
        new_text = new_text.replace("\n\n\n", "\n\n")

    block = "\n<noinclude>\n" + "\n".join(tags_in_order) + f"\n{FIXED_CAT_TAG}\n</noinclude>\n"
    new_text = new_text.rstrip() + block
    return new_text, f"wrap {len(tags_in_order)} stray tag(s) in noinclude"
