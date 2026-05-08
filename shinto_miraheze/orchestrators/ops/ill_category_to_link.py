"""
ill_category_to_link op
========================
Rewrites every ``{{ill|Category:X|...}}`` call to a bare
``[[Category:X]]`` category link.

Why
---
The ``{{ill}}`` template is for inline cross-language *article* links —
it renders a link to a local article (or a redlink with a foreign
fallback) plus a small superscript pointing at the foreign-language
version. It was never meant to target the Category namespace. When the
target is a ``Category:`` title, the template is being misused: editors
either wanted the page to be in that category and reached for the
wrong syntax, or imported wikitext from elsewhere brought along an
ill-wrapped category link from a context that didn't make sense here.

Either way the right local representation is the bare category link
``[[Category:X]]``. That puts the page into the category (which is
almost always the actual intent), removes a class of broken renders
(ill templates pointing at category targets render strangely), and
lets the rest of the cleanup pipeline reason about category membership
the normal way.

Resolution
----------
The local link target of an ``{{ill}}`` is, in priority order:

1. ``lt=`` (link target override) — last occurrence wins.
2. ``|1=`` named first positional — last occurrence wins.
3. The bare first positional.

If the resolved target starts with ``Category:`` (case-insensitive),
the whole template is replaced with ``[[Category:<rest>]]``. Other
``{{ill}}`` calls on the page are untouched.

Example::

    {{ill|Category:Kashima-jingu|lt=Category:Kashima-jingu|ja|Category:鹿島神宮|qid=Q128179399|1=Category:Kashima-jingu}}

becomes::

    [[Category:Kashima-jingu]]

Runs PRE_HEAVY so the converted text is what ``history_offload``
captures into the fandom mirror and XML archive snapshot.

Registered on every wikitext namespace because category-targeted ill
calls show up wherever ill calls show up — not just mainspace.
"""

import re

NAME = "ill_category_to_link"
# Same coverage as interlang_consolidate: every wikitext namespace,
# subject and talk side. Non-wikitext namespaces (geojson 420, module
# 828, item 860, property 862) don't carry templates so they're
# excluded.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)
PRE_HEAVY = True

# Conservative pattern (matches the rest of the ill-related ops): the
# body cannot contain nested ``{...}`` braces, which sidesteps needing
# a real wikitext parser. Calls with nested templates inside the body
# are left untouched — they're rare and not worth the parser dependency.
ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)


def _resolved_category_target(body: str) -> str | None:
    """Return the canonical ``Category:Foo`` title if this ill body's
    resolved local target is in the Category namespace, else None.

    Resolution priority (last-wins on duplicates, matching MediaWiki):
    ``lt=`` > ``|1=`` > bare first positional.
    """
    parts = body.split("|")
    if not parts:
        return None

    bare = parts[0].strip()
    one_override: str | None = None
    lt_override: str | None = None
    for p in parts[1:]:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        key = k.strip()
        if key == "1":
            one_override = v.strip()
        elif key == "lt":
            lt_override = v.strip()

    if lt_override is not None:
        target = lt_override
    elif one_override is not None:
        target = one_override
    else:
        target = bare

    if not target:
        return None
    head, sep, rest = target.partition(":")
    if not sep:
        return None
    if head.strip().lower() != "category":
        return None
    rest = rest.strip()
    if not rest:
        return None
    return f"Category:{rest}"


def apply(title: str, text: str):
    if not text:
        return None, None

    from ..common import REDIRECT_RE
    if REDIRECT_RE.search(text):
        return None, None

    changed_count = 0

    def replacer(match):
        nonlocal changed_count
        body = match.group(1)
        cat = _resolved_category_target(body)
        if cat is None:
            return match.group(0)
        changed_count += 1
        return f"[[{cat}]]"

    new_text = ILL_RE.sub(replacer, text)
    if new_text == text:
        return None, None

    return new_text, f"convert {changed_count} {{{{ill}}}} call(s) targeting Category: to plain category link"
