"""
interlang_consolidate op
=========================
Folds standalone interlanguage links like ``[[vi:Ất Mão]]`` into the
``{{wikidata link|Q...}}`` template on the same page as positional
parameter pairs ``|lang|title``.

Transformation examples
-----------------------
Before::

    [[vi:Ất Mão]]
    {{wikidata link|Q904791}}

After::

    {{wikidata link|Q904791|vi|Ất Mão}}

When the page has interlanguage links but no wikidata link template, a
new ``{{wikidata link||...}}`` (empty QID slot) is created — the template
definition is expected to categorise these into a maintenance category
so they can be noticed without running a separate scan script.

Two same-language interlanguage links with different titles are kept as
two distinct pairs (the template is expected to surface the conflict).
Same-language same-title duplicates are deduplicated.

Safety gate
-----------
Disabled by default because Template:Wikidata link must be updated to
accept the new positional pairs before this op runs in production —
otherwise pages edited by this op will display raw unparsed params
until the template catches up. Enable with ``ENABLE_INTERLANG_CONSOLIDATE=1``
once the template is deployed (use the git_synced sync workflow to edit
Template:Wikidata link in the repo, then let CI push it to the wiki).

Registered on every orchestrator (all namespaces) because user intent is
to consolidate interlang links wiki-wide, not just in mainspace.
"""

import os
import re

NAME = "interlang_consolidate"
# Every wikitext namespace — same coverage as history_offload.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)

# Interlanguage-link prefixes we will consolidate. Deliberately excludes
# non-language interwiki prefixes like ``d:`` (Wikidata), ``c:`` (Commons),
# ``wikt:`` (Wiktionary), ``m:`` (Meta) — those mean something different and
# must not be folded into the wikidata link template.
_LANGUAGE_CODES = frozenset([
    "en", "ja", "zh", "ko", "vi", "th", "ar", "de", "fr", "es", "it",
    "pt", "nl", "pl", "ru", "uk", "tr", "id", "ms", "fi", "sv", "no",
    "nb", "nn", "da", "cs", "hu", "el", "he", "hi", "bn", "fa", "ml",
    "ta", "te", "mr", "sa", "bo", "mn", "my", "km", "lo", "ka", "eu",
    "gl", "ca", "hr", "sr", "sl", "mk", "bg", "lv", "lt", "et", "sk",
    "ro", "is", "cy", "ga", "la", "be", "kk", "uz", "az", "hy", "eo",
    "sh", "bs", "simple",
    "zh-cn", "zh-tw", "zh-hk", "zh-hans", "zh-hant", "zh-yue",
    "sr-latn", "sr-cyrl",
])

# Standalone-line interlang link: allow leading/trailing whitespace and
# consume the trailing newline so removal collapses the whole line.
INTERLANG_RE = re.compile(
    r"^[ \t]*\[\[\s*([a-z]{2,3}(?:-[a-z]+)*)\s*:\s*([^\]|\n]+?)\s*\]\][ \t]*(?:\n|\Z)",
    re.MULTILINE,
)

# First {{wikidata link|...}} invocation on the page. The params group
# starts with the leading ``|`` so the split below is unambiguous.
WD_LINK_RE = re.compile(
    r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}",
    re.IGNORECASE,
)


def _parse_wd_params(raw: str) -> tuple[str, list[tuple[str, str]]]:
    """Split the captured ``|Q|lang|title|lang|title...`` into (qid, pairs).

    A trailing orphan (odd number of pair slots) is discarded — the template
    always takes language-title pairs, so a lone trailing value means the
    source was already malformed and we'd rather drop it than guess.
    """
    parts = [p.strip() for p in raw.split("|")[1:]]
    qid = parts[0] if parts else ""
    pair_parts = parts[1:]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i + 1 < len(pair_parts):
        pairs.append((pair_parts[i], pair_parts[i + 1]))
        i += 2
    return qid, pairs


def _build_wd_template(qid: str, pairs: list[tuple[str, str]]) -> str:
    parts = [qid]
    for lang, title in pairs:
        parts.append(lang)
        parts.append(title)
    return "{{wikidata link|" + "|".join(parts) + "}}"


def apply(title: str, text: str):
    if os.getenv("ENABLE_INTERLANG_CONSOLIDATE") != "1":
        return None, None
    if not text:
        return None, None

    interlang_matches = list(INTERLANG_RE.finditer(text))
    # Drop any prefix that isn't a known language code (interwiki-project
    # prefixes like ``d:`` have different semantics).
    valid = [m for m in interlang_matches if m.group(1).lower() in _LANGUAGE_CODES]
    if not valid:
        return None, None

    new_pairs = [(m.group(1).lower(), m.group(2).strip()) for m in valid]

    # Remove the interlang links right-to-left so earlier offsets stay
    # valid while we mutate.
    text_no_il = text
    for m in reversed(valid):
        text_no_il = text_no_il[:m.start()] + text_no_il[m.end():]
    # Collapse runs of blank lines the removals may have created.
    text_no_il = re.sub(r"\n{3,}", "\n\n", text_no_il)

    wd_match = WD_LINK_RE.search(text_no_il)
    if wd_match:
        qid, existing_pairs = _parse_wd_params(wd_match.group(1))
        merged = list(existing_pairs)
        for pair in new_pairs:
            if pair not in merged:
                merged.append(pair)
        new_template = _build_wd_template(qid, merged)
        new_text = text_no_il[:wd_match.start()] + new_template + text_no_il[wd_match.end():]
    else:
        # No existing template — create one with empty QID slot so the
        # template can surface the page in a "has interlang but no QID"
        # maintenance category.
        new_template = _build_wd_template("", new_pairs)
        new_text = text_no_il.rstrip() + "\n" + new_template + "\n"

    if new_text == text:
        return None, None
    return new_text, f"consolidate {len(new_pairs)} interlanguage link(s) into wikidata link template"
