"""
english_to_kana.py — deterministic English label -> hiragana reading.

The INVERSE of ``kana_english.py``. That module builds an English label from a
kana reading; this one builds a kana reading from an English label. It exists
because of CLAUDE.md's rule:

    "Once something has an English label, it's graduated past the point that we
    care about its KANA reading. It is done. There's no KANA reading because the
    English label IS the KANA reading!"
    "Do not try to reason about what the KANA reading would be on something with
    an English label."

So where a kana value IS wanted on an en-labelled item, it is DERIVED
mechanically — English label for the stem, Japanese label for the shrine-type
suffix — and never read out of an article. Emma, 2026-09-09: *"derive the Kana
from the English-language labels combined with whatever the standard
transliteration is of the other stuff."*

Two halves:

  1. ``romaji_to_hiragana`` — macron-free Hepburn back to kana, by inverting
     ``kana_english.HEPBURN``. Longest-mora-first, with the moraic nasal
     (``n`` before a consonant, ``n'``, word-final ``n``) and the geminate
     (doubled consonant, ``tch``) handled explicitly.
  2. ``kana_for`` — split the English label into stem + shrine-type word, take
     the matching kana suffix from the KANJI label, and join.

The suffix is decided by the kanji, exactly as in ``kana_english``: the English
word "Shrine" alone cannot tell 神社 (じんじゃ) from 社 (しゃ) from 宮 (ぐう), and
天神社 is a documented trap — its split is 天神 + 社, not 天 + 神社, so stripping
" Shrine" off "Anazawa Tenjin Shrine" and appending じんじゃ would emit
あなざわてんじんじんじゃ.

CONSERVATIVE BY DESIGN, same as its sibling: an unknown suffix, a romaji stem
that will not tokenize, or an English label that does not end in the expected
shrine word all return None, so the item is left alone rather than given a
guessed reading.

⚠ KNOWN LOSS: the repo's English labels are macron-free Hepburn (Kyoto, not
Kyōto), so a long vowel is unrecoverable from the label — おおやま and おやま both
romanize to "Oyama". The derived reading therefore carries the SHORT vowel. That
is a property of deriving from the label at all, not a bug here; it is why this
module refuses anything it is not confident about rather than guessing length.
"""

import re
from typing import Optional

from kana_english import HEPBURN


# ---- romaji -> hiragana ------------------------------------------------------

def _build_inverse():
    """Invert HEPBURN. Several kana share a romanization (じ/ぢ -> ji, ず/づ -> zu,
    お/を -> o); the modern standard spelling wins, so a derived reading never
    emits a historical-orthography kana we did not read anywhere."""
    canonical = {
        "ji": "じ", "zu": "ず", "o": "お", "i": "い", "e": "え", "u": "う", "a": "あ",
    }
    inv = {}
    for kana, romaji in HEPBURN.items():
        if romaji in canonical:
            continue
        if kana in "ぁぃぅぇぉ":
            continue  # small vowels: only ever produced as part of a yoon
        inv.setdefault(romaji, kana)
    inv.update(canonical)
    return inv


_INVERSE = _build_inverse()
_MORA = sorted(_INVERSE, key=len, reverse=True)  # longest first: "kyo" before "ki"
_VOWELS = set("aeiou")
_MACRONS = {"ō": "o", "ū": "u", "ā": "a", "ē": "e", "ī": "i",
            "ô": "o", "û": "u", "â": "a", "ê": "e", "î": "i"}


def romaji_to_hiragana(token: str) -> Optional[str]:
    """Macron-free Hepburn -> hiragana. None if any part will not tokenize.

    ``Kasano`` -> かさの. ``Zeb`` -> None (a stranded consonant: the impossible
    cluster romaji_phonology exists to reject)."""
    s = (token or "").strip().lower()
    for macron, plain in _MACRONS.items():
        s = s.replace(macron, plain)
    if not s:
        return None
    out = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        # apostrophe after a moraic nasal: shin'ichi -> しんいち
        if ch == "'":
            i += 1
            continue
        # geminate: doubled consonant, or the 'tch' cluster (っち)
        if i + 1 < n and ch == s[i + 1] and ch not in _VOWELS and ch != "n":
            out.append("っ")
            i += 1
            continue
        if ch == "t" and s[i + 1:i + 3] == "ch":
            out.append("っ")
            i += 1
            continue
        # moraic nasal: 'n' not starting a na-row / nya mora
        if ch == "n":
            nxt = s[i + 1:i + 2]
            if nxt not in _VOWELS and nxt != "y":
                out.append("ん")
                i += 1
                continue
        for mora in _MORA:
            if s.startswith(mora, i):
                out.append(_INVERSE[mora])
                i += len(mora)
                break
        else:
            return None
    return "".join(out)


# ---- shrine-type suffixes ----------------------------------------------------
#
# (kanji suffix on the ja label, kana suffix, English suffix phrases).
# Most specific kanji FIRST, and within an entry the longest English phrase
# first, so 天神社/"Tenjin Shrine" is matched before 神社/"Shrine".
#
# 大社 is deliberately absent: it reads たいしゃ on some shrines and おおやしろ on
# others (出雲大社 = いずもおおやしろ, which docs/kana_name_mate_rulings.md records
# a selector getting wrong), and the English "Grand Shrine" cannot tell them
# apart. 神宮 is absent for the stem-boundary reason kana_english already gives.
# 神 is absent because Emma ruled 四至神 -> ミヤノメグリノカミ correct as it stands:
# a ~神 item's reading is not a shrine-suffix problem.
_SUFFIXES = [
    ("大神宮", "だいじんぐう", ["Daijingu"]),
    ("大神社", "だいじんじゃ", ["Daijinja"]),
    # Emma 2026-08-24 (ATOMIC_FILES note on tenjinsha_en_labels.txt): the label
    # records which of the two attested readings the item carries --
    # てんじんしゃ -> "Tenjin-sha", てんじんじゃ -> "Tenjin Shrine". Read backwards
    # here, that mapping is the only per-item information there is.
    ("天神社", "てんじんしゃ", ["Tenjin-sha", "Tenjinsha"]),
    # WARNING: jawiki gives 穴澤天神社 as あなざわてんじんしゃ, i.e. "Tenjin Shrine"
    # does NOT reliably mean てんじんじゃ on a given item -- both readings are
    # attested and the English label was applied in one bulk batch, so it carries
    # no per-item information. Emma left 天神社 undecided
    # (docs/kana_name_mate_rulings.md). Kept for completeness; do not point a bulk
    # job at this entry without settling that first.
    ("天神社", "てんじんじゃ", ["Tenjin Shrine"]),
    ("天満宮", "てんまんぐう", ["Tenmangu", "Tenman-gu"]),
    ("八幡宮", "はちまんぐう", ["Hachimangu", "Hachiman-gu"]),
    ("神社", "じんじゃ", ["Shrine"]),
    ("宮", "ぐう", ["-gu Shrine"]),
    ("社", "しゃ", ["-sha Shrine"]),
]

_PAREN = re.compile(r"\s*\([^)]*\)\s*$")


def kana_for(ja: str, en: str) -> Optional[str]:
    """Derive the hiragana reading of a shrine from its Japanese label (which
    picks the shrine-type suffix) and its English label (which supplies the
    romanized stem). None when nothing can be derived confidently."""
    ja = (ja or "").strip()
    en = _PAREN.sub("", (en or "").strip())  # drop "(Kaga Province)" disambiguators
    if not ja or not en:
        return None
    # Entries are grouped by kanji suffix: 天神社 has two, one per attested
    # reading, and BOTH have to be offered the English label before the kanji
    # suffix is declared a non-match. Returning at the first entry would make
    # "Anazawa Tenjin Shrine" unreachable, since てんじんしゃ is listed first.
    matched_kanji = None
    for kanji_suf, kana_suf, en_phrases in _SUFFIXES:
        if not ja.endswith(kanji_suf):
            continue
        if matched_kanji is None:
            matched_kanji = kanji_suf
        elif kanji_suf != matched_kanji:
            break  # a shorter, less specific kanji suffix -- the first one won
        for phrase in sorted(en_phrases, key=len, reverse=True):
            if not en.endswith(phrase):
                continue
            stem_romaji = en[: -len(phrase)].strip(" -")
            if not stem_romaji:
                return None
            if " " in stem_romaji:
                # A multi-word stem is not a single romanized name -- it is a
                # gloss or an un-stripped disambiguator ("Ichinomiya Shrine
                # Yokohama"). Refuse rather than concatenate words into a
                # reading that was never a reading.
                return None
            stem = romaji_to_hiragana(stem_romaji)
            if not stem:
                return None
            return stem + kana_suf
    return None
