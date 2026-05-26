"""
canonicalize_template_case op
=============================
Rewrites references to known case-collision templates so they point at
the **canonical capitalised form** rather than a stray lowercase
variant. MediaWiki treats the first character of a template name as
case-insensitive (``{{infobox X}}`` and ``{{Infobox X}}`` resolve to
the same page), but subsequent-word capitalisation **is** case-sensitive
— ``Template:Infobox organization`` and ``Template:Infobox Organization``
are two different wiki pages. The sync has produced both case-variants
of certain ``Template:Infobox X`` pages, which jammed Windows git
operations on this repo (see ``docs/case_collision_report.md``).

Approach: per (lowercase form, canonical form) pair in
``TEMPLATE_CANONICAL``, build two regexes — one for transclusions,
one for ``[[Template:…]]`` wikilinks — that:

* allow the ``Template:`` prefix optionally, with any casing on the T;
* allow the first character of the template name to be either case
  (so ``infobox`` and ``Infobox`` both match);
* require the **rest** of the name to match exactly the lowercase
  variant (so ``organization`` matches and ``Organization`` does not).

Then rewrite the matched prefix to the canonical form, leaving the
parameter block / closing brackets untouched (same pattern
``untransclude_crud_templates.py`` uses). This naturally preserves
parameters and nested templates.

Runs on **every namespace** any orchestrator covers (mainspace through
talk; ns=8 MediaWiki excluded per the project-wide convention). Once
every page in every namespace has been normalised, the lowercase
``Template:Infobox …`` pages on the wiki have zero remaining references
and can be cleaned up wiki-side (Emma's plan).

When new collisions surface (re-run
``shinto_miraheze/case_collision_report.py``), add the pair to
``TEMPLATE_CANONICAL``.
"""

import re

from ..common import REDIRECT_RE

NAME = "canonicalize_template_case"
PRE_HEAVY = True

# Every namespace covered by any orchestrator except ns=8 (MediaWiki —
# excluded everywhere per CLAUDE.md "ns=8 MediaWiki is intentionally
# excluded from every orchestrator"). Includes subject-side and
# talk-side namespaces, plus the non-wikitext namespaces (where the
# regex will be a no-op every time but registering for completeness).
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7,  # main + talk + user + talk + project + talk + file + talk
    9, 10, 11, 12, 13, 14, 15,  # mediawiki-talk + template + talk + help + talk + category + talk
    420, 421,  # geojson + talk
    828, 829,  # module + talk
    860, 861,  # item + talk
    862, 863,  # property + talk
)

# (lowercase form, canonical form) pairs. Derived from
# docs/case_collision_report.md — every blob hash was IDENTICAL so
# canonicalising is a purely cosmetic / pointer-normalising rewrite.
TEMPLATE_CANONICAL = {
    "Infobox chinese": "Infobox Chinese",
    "Infobox film": "Infobox Film",
    "Infobox historic site": "Infobox Historic Site",
    "Infobox holiday": "Infobox Holiday",
    "Infobox kofun": "Infobox Kofun",
    "Infobox mountain": "Infobox Mountain",
    "Infobox museum": "Infobox Museum",
    "Infobox noble": "Infobox Noble",
    "Infobox officeholder": "Infobox Officeholder",
    "Infobox organization": "Infobox Organization",
}


def _name_pattern(name: str) -> str:
    """Regex fragment matching ``name`` with MediaWiki normalisation:
    first character case-insensitive, underscore/space interchangeable
    everywhere, every other character exact-cased.

    Critically: only the FIRST char is case-folded. The whole point of
    this op is that the second-word casing IS significant on MediaWiki,
    so we must NOT case-fold the rest of the name."""
    if not name:
        return ""
    first, rest = name[0], name[1:]
    if first.isalpha():
        first_pat = f"[{first.upper()}{first.lower()}]"
    elif first in " _":
        first_pat = r"[ _]+"
    else:
        first_pat = re.escape(first)
    # MediaWiki normalises consecutive spaces/underscores in titles, so
    # match runs (one-or-more) rather than a single whitespace char.
    pieces: list[str] = []
    i = 0
    while i < len(rest):
        if rest[i] in " _":
            j = i
            while j < len(rest) and rest[j] in " _":
                j += 1
            pieces.append(r"[ _]+")
            i = j
        else:
            pieces.append(re.escape(rest[i]))
            i += 1
    return first_pat + "".join(pieces)


def _build_transclusion_re(name: str) -> re.Pattern:
    """Match the prefix of ``{{[Template:]name``, lookahead for ``|`` or
    ``}}`` so the parameter block / closing braces stay untouched. The
    trailing-whitespace check is inside the lookahead (non-consuming) so
    any space before ``|`` is preserved verbatim in the output."""
    return re.compile(
        rf"\{{\{{\s*(?:[Tt]emplate\s*:\s*)?{_name_pattern(name)}(?=\s*\||\s*\}}\}})"
    )


def _build_wikilink_re(name: str) -> re.Pattern:
    """Match the target-prefix of ``[[Template:name``, lookahead for
    ``|`` or ``]]`` so display text / closing brackets stay untouched.
    Trailing-whitespace check inside the lookahead — preserved verbatim."""
    return re.compile(
        rf"\[\[\s*:?\s*[Tt]emplate\s*:\s*{_name_pattern(name)}(?=\s*\||\s*\]\])"
    )


# Pre-compile at import: list of (canonical, transclusion_re, wikilink_re).
_REWRITERS: list[tuple[str, re.Pattern, re.Pattern]] = [
    (canonical, _build_transclusion_re(lower), _build_wikilink_re(lower))
    for lower, canonical in TEMPLATE_CANONICAL.items()
]


def apply(title: str, text: str):
    # Don't touch the template pages themselves — both case-variants are
    # currently real pages on the wiki, and the lowercase ones may carry
    # docs / examples that legitimately reference the lowercase name.
    # Once Emma resolves the wiki side, we can drop this guard.
    if title.lower().startswith("template:infobox "):
        return None, None
    if REDIRECT_RE.search(text):
        # Redirects are single-line `#REDIRECT [[Target]]` — they CAN
        # point at a lowercase template variant and should be rewritten
        # there, but we conservatively skip to match the convention of
        # most other ops. If a redirect ever points at a lowercase
        # variant, it'll surface in the case-collision report.
        return None, None

    new_text = text
    changes: list[str] = []
    for canonical, t_re, l_re in _REWRITERS:
        t_count = len(t_re.findall(new_text))
        if t_count:
            new_text = t_re.sub("{{" + canonical, new_text)
            changes.append(f"{{{{{canonical}}}}}×{t_count}")
        l_count = len(l_re.findall(new_text))
        if l_count:
            new_text = l_re.sub(f"[[Template:{canonical}", new_text)
            changes.append(f"[[Template:{canonical}]]×{l_count}")

    if new_text == text:
        return None, None
    return new_text, "canonicalise Template:Infobox case (" + ", ".join(changes) + ")"
