"""
romaji_phonology.py — Japanese-phonology validator for romaji labels (queue #8).

Emma 2026-07-06: a cloud agentic session emitted a garbage romaji label
`Zebshō-ji Temple` (the `Zeb` cluster is phonologically impossible — in Japanese
only the moraic nasal `n` can close a syllable; `b` cannot be a coda). This module
rejects romaji that does NOT decompose into a valid sequence of Japanese mora, so
new labels can be gated and existing bad ones flagged.

The mora inventory IS the Hepburn romanization table (``kana_english.HEPBURN``
values) — the exact set of syllables the transliteration pipeline can produce.
A token is valid iff it tokenizes left-to-right into those syllables, allowing:
  * standalone vowels and the moraic nasal ``n`` (both are table entries),
  * long vowels (a repeated vowel is just two vowel mora, e.g. ``oo`` = o+o),
  * geminates (a doubled consonant / the ``tch`` cluster = the small-tsu),
  * macrons (``ō ū ā ē ī``) normalized to plain vowels first.

Anything that leaves a stranded consonant (``Zeb`` → ``ze`` + stranded ``b``) is
invalid. Full labels contain English type-words (Shrine, Grand, Temple, Jingu…);
those are skipped, and only the romaji stem tokens are validated.
"""

import re

from kana_english import HEPBURN

# The valid mora inventory: every romaji syllable the kana table can emit.
_SYLLABLES = sorted(set(HEPBURN.values()), key=len, reverse=True)  # longest first
_VOWELS = set("aeiou")
_MACRONS = {"ō": "o", "ū": "u", "ā": "a", "ē": "e", "ī": "i",
            "ô": "o", "û": "u", "â": "a", "ê": "e", "î": "i"}

# English type/qualifier words that appear in built labels and are NOT romaji.
_ENGLISH_WORDS = {
    "shrine", "shrines", "grand", "temple", "temples", "great", "mountain",
    "jingu", "jinja", "taisha", "daijinja", "daijingu", "gu", "sha",
    "of", "the", "and", "no", "kami", "river", "mount", "castle", "island",
}


def _normalize(token: str) -> str:
    s = token.lower()
    for m, v in _MACRONS.items():
        s = s.replace(m, v)
    return s


def is_valid_romaji_mora(token: str) -> bool:
    """True iff ``token`` decomposes into a valid sequence of Japanese mora.

    ``Mefu`` -> me+fu -> True. ``Zeb`` -> ze + stranded ``b`` -> False.
    ``Nikko`` -> ni + (geminate) + ko -> True."""
    s = _normalize(token)
    if not s or not s.isalpha():
        return False
    i, n = 0, len(s)
    while i < n:
        # geminate: doubled consonant, or the special 'tch' (った→tta, っち→tchi)
        if i + 1 < n and s[i] == s[i + 1] and s[i] not in _VOWELS and s[i] != "n":
            i += 1
            continue
        if s[i] == "t" and s[i + 1:i + 3] == "ch":
            i += 1
            continue
        # match the longest syllable in the inventory at position i
        for syl in _SYLLABLES:
            if s.startswith(syl, i):
                i += len(syl)
                break
        else:
            return False
    return True


def is_valid_label(label: str) -> bool:
    """Validate a full built label: every romaji (non-English-word) token must be
    valid mora. English type-words (Shrine, Grand, Jingu…) are skipped."""
    for tok in re.split(r"[ \-]+", (label or "").strip()):
        if not tok:
            continue
        if tok.lower() in _ENGLISH_WORDS:
            continue
        if not is_valid_romaji_mora(tok):
            return False
    return True
