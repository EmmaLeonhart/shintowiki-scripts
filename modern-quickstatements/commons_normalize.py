"""commons_normalize — a Wikimedia Commons category name → house-style English label.

A **mid-pipeline fallback** stage (Emma, 2026-07-10): it fires only after the earlier,
higher-confidence stages (an existing English label, then kana derivation) have produced
nothing. Because everything more reliable has already been tried, an imperfect result here
is acceptable — the alternative is no label at all.

Scope: Japanese Shinto shrines and Japanese Buddhist temples only. Input is the Commons
category name, which for these subjects is Latin-script romaji ("Kiyomizu-dera",
"Meiji Jingu", "Sensouji"). Output is the house-style English label, or None when the name
is not confidently a shrine/temple (no recognised suffix, or non-Latin residue in the stem).

Long vowels: **transcribe what the romaji marks, never guess what it doesn't.**
    Sensouji  -> "Sensō-ji Temple"   (the spelled `ou` becomes `ō`)
    Sensoji   -> "Senso-ji Temple"   (bare `o`, left plain — the acceptable missed macron)

Design/spec: docs/superpowers/specs/2026-07-10-commons-romaji-normalization-design.md
"""
import re
from typing import Optional

# ── long-vowel transcription ────────────────────────────────────────────────
# Marked long vowels in the romaji spelling → macron. Order matters only in that each is a
# self-contained 2→1 substitution. This is best-effort: it will occasionally add a macron
# where the "ou" is really an o+u boundary (Inoue → Inōe). Emma accepts that; the accuracy
# report measures it before any edit is proposed.
_LONG_VOWELS = (("ou", "ō"), ("oo", "ō"), ("uu", "ū"))


def transcribe_long_vowels(s: str) -> str:
    for pair, macron in _LONG_VOWELS:
        s = s.replace(pair, macron)
    return s


# ── suffix conventions (romaji analogues of temple_english / kana_english) ───
# Temple: "<Stem>-<suffix> Temple".  Longest ending first so `dera`/`tera` beat `ji` etc.
_TEMPLE_SUFFIXES = ("dera", "tera", "ji", "in", "an", "do", "bo")

# Shrine *words* (usually a separate token). Longest first so `daijinja` beats `jinja` and
# `jingu`/`taisha` beat the short attached `-gu`/`-sha` below.
_SHRINE_WORDS = (
    ("daijingu", "Daijingu"),      # 大神宮 — before "jingu" so it isn't split dai+jingu
    ("daijinja", "Daijinja"),
    ("jinja", "Shrine"),
    ("jingu", "Grand Shrine"),
    ("taisha", "Grand Shrine"),
)
# Shrine *attached* suffixes: "<Stem>-<suffix> Shrine".
_SHRINE_ATTACHED = ("sha", "gu")

_BRACKETS = re.compile(r"\s*[（(〔][^）)〕]*[）)〕]")
_LATIN_STEM = re.compile(r"^[A-Za-zŌŪĀĪĒōūāīē'’.\- ]+$")


def _strip(name: str) -> str:
    """Drop 'Category:', a comma-disambiguator (", Nagasaki"), and bracketed disambiguators."""
    if name.startswith("Category:"):
        name = name[len("Category:"):]
    name = _BRACKETS.sub("", name)            # brackets first: "(Naka-ku, Nagoya)" has a comma
    name = name.split(",")[0]                  # then a bare ", Nagasaki" / ", Akasaka"
    return re.sub(r"\s+", " ", name).strip()


def _macron_free(s: str) -> str:
    return s.translate(str.maketrans("āīūēōĀĪŪĒŌ", "aiueoAIUEO"))


# Some Commons names use a circumflex for a long vowel (Ten'man-gû, Tôfuku-ji). Fold it to
# the macron the house style uses (Emma, 2026-07-10).
_CIRCUMFLEX = str.maketrans("âêîôûÂÊÎÔÛ", "āēīōūĀĒĪŌŪ")


def normalize(commons_name: str) -> Optional[str]:
    """Commons category name → house English label.

    Returns None only for an empty name or one with no Latin letters (a kanji Commons name
    belongs to the kana stage upstream). Otherwise ALWAYS returns a label: when no shrine/
    temple suffix is recognised, it appends " Shrine" (Emma, 2026-07-10: "if you cannot find
    the word shrine or something in it then you just add ' Shrine' at the end of it" — this
    is how Buddhist devotional names like Kannon/Daishi go through the pipeline too).
    """
    name = _circumflex_to_macron(_strip(commons_name or ""))
    if not name:
        return None
    if not any("a" <= c.lower() <= "z" for c in name):   # kanji Commons name → kana stage
        return None

    low = _macron_free(name).lower()

    # Already carries an English classificatory suffix (any case, hyphen or space) — keep
    # the reading, canonicalise the suffix. Temples keep their romaji suffix in the stem
    # ("Kōfuku-ji Temple"); shrines get the house " Shrine"/" Grand Shrine".
    for token, house in (("grand shrine", "Grand Shrine"), ("shrine", "Shrine"),
                         ("temple", "Temple")):
        if low.endswith(token) or low.endswith(token.replace(" ", "-")):
            cut = len(token)
            stem = name[: len(name) - cut].rstrip(" -")
            if not stem:
                return None
            return "{} {}".format(transcribe_long_vowels(stem), house)

    # Shrine words first (they can contain the short attached suffixes).
    for ending, house in _SHRINE_WORDS:
        if low.endswith(ending):
            stem = name[: len(name) - len(ending)].rstrip(" -")
            return _shrine(stem, house)

    # Temple suffixes. Guard the short risky ones: "-in" must not fire on "...jin"
    # (myojin 明神, tenjin 天神 are shrine words, not 院).
    for ending in _TEMPLE_SUFFIXES:
        if low.endswith(ending):
            if ending == "in" and low.endswith("jin"):
                continue
            stem = name[: len(name) - len(ending)].rstrip(" -")
            if not stem:
                return None
            return "{}-{} Temple".format(transcribe_long_vowels(stem), ending)

    # Short attached shrine suffixes.
    for ending in _SHRINE_ATTACHED:
        if low.endswith(ending):
            stem = name[: len(name) - len(ending)].rstrip(" -")
            if not stem:
                return None
            return "{}-{} Shrine".format(transcribe_long_vowels(stem), ending)

    # No suffix recognised — the established default is to append " Shrine".
    return "{} Shrine".format(transcribe_long_vowels(name))


def _circumflex_to_macron(s: str) -> str:
    return s.translate(_CIRCUMFLEX)


def _shrine(stem: str, house: str) -> Optional[str]:
    if not stem or not _LATIN_STEM.match(stem):
        return None
    return "{} {}".format(transcribe_long_vowels(stem), house)
