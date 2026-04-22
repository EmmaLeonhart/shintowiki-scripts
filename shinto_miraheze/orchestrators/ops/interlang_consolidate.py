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
new ``{{wikidata link||...}}`` (empty QID slot) is created so the
interwikis still render — the empty slot stays until someone supplies
the QID.

Duplicate handling (per user spec):
  * Same-language same-title pairs are dropped as duplicates.
  * Same-language DIFFERENT-title pairs are kept, preserving both
    distinct links.
  * If the resulting pair list contains any duplicate language code,
    the op adds ``[[Category:Pages with interwikis with duplicate
    languages]]`` to the page so those pages are discoverable for
    cleanup. The category is also removed again if a later run finds
    no duplicates.
Pairs are appended in the order interlanguage links appear on the
page (top-down), so chronology on the source page is preserved.

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

DUP_LANG_CATEGORY = "[[Category:Pages with interwikis with duplicate languages]]"


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


def _has_duplicate_languages(pairs: list[tuple[str, str]]) -> bool:
    """True if any language code appears in more than one pair."""
    langs = [lang for lang, _ in pairs]
    return len(langs) != len(set(langs))


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
        final_pairs = merged
    else:
        # No existing template — create one with empty QID slot. The
        # interwikis still render; a later run or manual edit can fill
        # in the QID.
        new_template = _build_wd_template("", new_pairs)
        new_text = text_no_il.rstrip() + "\n" + new_template + "\n"
        final_pairs = new_pairs

    # Maintenance: flag pages that wound up with the same language code
    # on multiple pairs (different targets). Add or remove the category
    # so the invariant stays truthful across re-runs.
    has_dup = _has_duplicate_languages(final_pairs)
    cat_present = DUP_LANG_CATEGORY in new_text
    if has_dup and not cat_present:
        new_text = new_text.rstrip() + "\n" + DUP_LANG_CATEGORY + "\n"
    elif not has_dup and cat_present:
        new_text = new_text.replace(DUP_LANG_CATEGORY + "\n", "")
        new_text = new_text.replace(DUP_LANG_CATEGORY, "")

    if new_text == text:
        return None, None
    summary = f"consolidate {len(new_pairs)} interlanguage link(s) into wikidata link template"
    if has_dup:
        summary += " (has duplicate-language pairs)"
    return new_text, summary
