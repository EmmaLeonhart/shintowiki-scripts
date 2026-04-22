"""
untranslated_japanese op
=========================
Ported from ``shinto_miraheze/tag_untranslated_japanese.py``. Counts
Japanese characters (hiragana, katakana, CJK ideographs) outside of
expected contexts (templates, interwiki links, refs, categories, etc.)
and applies bucketed categories:

    [[Category:Pages with 50+ untranslated japanese characters]]
    [[Category:Pages with 100+ untranslated japanese characters]]
    ...
    [[Category:Pages with 5000+ untranslated japanese characters]]

Also strips the legacy flat ``[[Category:Pages with untranslated japanese
content]]`` tag if present.

Mainspace-only. Redirect + interwiki skipping is handled by the
orchestrator's common loop, so this op just does text analysis and
returns the rewritten text (or (None, None) if nothing changed).

The standalone ``tag_untranslated_japanese.py`` script is kept in the
repo for the one-off ``--category`` re-bucketing mode that
``wiki-cleanup.yml`` still invokes; its main scheduled sweep is
replaced by this op.
"""

import re

NAME = "untranslated_japanese"
NAMESPACES = (0,)

THRESHOLDS = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]

OLD_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages with untranslated japanese content\s*\]\]\n?",
    re.IGNORECASE,
)

BUCKET_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Pages with \d+\+ untranslated japanese characters\s*\]\]\n?",
    re.IGNORECASE,
)

# Contexts to strip before counting — Japanese inside these is expected and
# shouldn't be flagged as untranslated content.
_STRIP_PATTERNS = [
    re.compile(r"^==\s*[^=]*\(P\d+\)\s*==.*?(?=^==\s*[^=]|\Z)", re.DOTALL | re.MULTILINE),
    re.compile(r"\{\|.*?\|\}", re.DOTALL),
    re.compile(r"\[\[[a-z]{2,}:[^\]]*\]\]", re.IGNORECASE),
    re.compile(r"<!--.*?-->", re.DOTALL),
    re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<ref[^>]*/>", re.IGNORECASE),
    re.compile(r"<nowiki>.*?</nowiki>", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[\[\s*Category\s*:[^\]]*\]\]", re.IGNORECASE),
    re.compile(r"\[\[\s*(?:File|Image)\s*:[^\]]*\]\]", re.IGNORECASE),
    re.compile(r"<gallery[^>]*>.*?</gallery>", re.DOTALL | re.IGNORECASE),
]

_INNERMOST_TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}", re.DOTALL)


def _strip_templates(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _INNERMOST_TEMPLATE_RE.sub("", text)
    return text


def _count_japanese_chars(text: str) -> int:
    count = 0
    for ch in text:
        cp = ord(ch)
        if (
            0x3040 <= cp <= 0x309F
            or 0x30A0 <= cp <= 0x30FF
            or 0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF
        ):
            count += 1
    return count


def _count_after_strip(text: str) -> int:
    stripped = text
    for pattern in _STRIP_PATTERNS:
        stripped = pattern.sub("", stripped)
    stripped = _strip_templates(stripped)
    return _count_japanese_chars(stripped)


def _desired_cats(jp_count: int) -> list[str]:
    return [
        f"[[Category:Pages with {t}+ untranslated japanese characters]]"
        for t in THRESHOLDS
        if jp_count >= t
    ]


def apply(title: str, text: str):
    jp_count = _count_after_strip(text)
    desired = _desired_cats(jp_count)

    # Current state of the page.
    has_old = bool(OLD_CAT_RE.search(text))
    existing_buckets = {m.group(0).rstrip("\n") for m in BUCKET_CAT_RE.finditer(text)}
    desired_set = set(desired)

    # Cheap-exit cases.
    if not has_old and existing_buckets == desired_set:
        return None, None

    # Rewrite: strip old flat category + all bucket cats, then re-append
    # the desired buckets at the end.
    new_text = text
    if has_old:
        new_text = OLD_CAT_RE.sub("", new_text)
    new_text = BUCKET_CAT_RE.sub("", new_text)

    if desired:
        new_text = new_text.rstrip() + "\n" + "\n".join(desired) + "\n"
    else:
        new_text = new_text.rstrip() + "\n"

    if new_text == text:
        return None, None

    bucket_labels = [f"{t}+" for t in THRESHOLDS if jp_count >= t]
    if bucket_labels:
        fragment = f"update Japanese content tags ({jp_count} JP chars: {', '.join(bucket_labels)})"
    else:
        fragment = f"remove Japanese content tags ({jp_count} JP chars)"
    return new_text, fragment
