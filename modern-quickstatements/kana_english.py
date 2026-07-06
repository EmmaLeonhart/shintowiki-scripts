"""
kana_english.py — deterministic kana -> English Shinto-shrine label (Stage 1).

Stage 1 of the English-label pipeline (see docs/english_label_pipeline.md):
for a shrine that has a Japanese label + kana reading but no English label,
build the English label by deterministic rules from the kana — no LLM, no
pykakasi/Indonesian library.

Emma's literal suffix conventions (anglicise but preserve):
    jinja     -> "<Stem> Shrine"
    jingu     -> "<Stem> Grand Shrine"  (+ alias "<Stem> Jingu")
    taisha    -> "<Stem> Grand Shrine"  (+ alias "<Stem> Taisha")
    daijinja  -> "<Stem> Daijinja"
    -sha      -> "<Stem>-sha Shrine"
    -gu       -> "<Stem>-gu Shrine"

The stem is romanized to macron-free Hepburn (English-Wikipedia convention:
long vowels ou/oo/uu collapse to o/o/u, e.g. Kyoto, not Kyōto). The shrine-type
suffix is matched on the *kanji* label, not the kana: the kana じんぐう alone
can't separate 明治/神宮 (Meiji Jingū) from 天神/宮 (Tenjin-gū). Most specific
kanji first, so 大神宮 beats 神宮 and 神社 beats bare 社.

DEFERRAL: pure 神宮 (jingū) has a genuinely ambiguous stem boundary even in
kanji, so it is NOT labelled here — it returns None and falls through to the
LLM stage rather than risk a wrong label like "Ten Jingu". (Only ~2 such items
in the current backlog; most 〇〇神宮 grand shrines already have en labels.)
大神宮 is handled as a transliterated "<Stem> Daijingu".

CONSERVATIVE BY DESIGN: anything we cannot confidently handle — unknown
suffix, unromanizable stem (kanji left in the reading), empty stem — returns
None, so the shrine falls through to a later pipeline stage rather than
getting a wrong label onto Wikidata.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional


@dataclass
class LabelResult:
    label: str
    alias: Optional[str] = None


# ---- time-boxed Engishiki name overrides (Emma 2026-07-06, queue #9) ----
#
# A handful of Engishiki shrine names have a well-known reading glitch: the ja
# label carries a wrong/absent kana reading, so the deterministic romanizer
# would produce the wrong stem (or nothing at all). For those exact ja labels we
# force the correct standard English label regardless of kana. 売布 reads "Mefu"
# (not "Urifu"/"Baifu"), so every 売布神社 item is "Mefu Shrine".
#
# This is a standardisation nudge, NOT a permanent rule — it should only run for
# three years. After the expiry it no-ops; retire it then (delete the override +
# its test).
_HARDCODED_LABELS = {
    "売布神社": "Mefu Shrine",
}
_HARDCODED_EXPIRY = date(2029, 7, 6)


def hardcoded_label(ja: str, today: Optional[date] = None) -> Optional[str]:
    """Return a forced English label for a known glitchy Engishiki name, or None.
    Time-boxed (see ``_HARDCODED_EXPIRY``); returns None once expired so the
    override retires on its own. ``today`` is injectable for tests."""
    today = today or datetime.now(timezone.utc).date()
    if today >= _HARDCODED_EXPIRY:
        return None
    return _HARDCODED_LABELS.get((ja or "").strip())


# ---- proper Hepburn (NOT the tokiponizer table, which collapses zu->su) ----

HEPBURN = {
    # vowels
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    # k / g
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    # s / z
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    # t / d
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    # n
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    # h / b / p
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    # m
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    # y
    "や": "ya", "ゆ": "yu", "よ": "yo",
    # r
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    # w / n
    "わ": "wa", "ゐ": "wi", "ゑ": "we", "を": "o",
    "ん": "n",
    # small vowels standing alone (rare)
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}


def katakana_to_hiragana(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:  # katakana block with hiragana counterparts
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def _collapse_long_vowels(romaji: str) -> str:
    prev = None
    while prev != romaji:
        prev = romaji
        romaji = romaji.replace("ou", "o").replace("oo", "o").replace("uu", "u")
    return romaji


def romanize(kana: str) -> Optional[str]:
    """Kana -> macron-free Hepburn, Title Case. None if any char is unmappable."""
    h = katakana_to_hiragana(kana)
    out = []
    i = 0
    geminate = False
    while i < len(h):
        ch = h[i]
        if ch == "っ":  # small tsu: geminate the next consonant
            geminate = True
            i += 1
            continue
        if ch == "ー":  # prolonged sound mark: repeat the previous vowel
            if out and out[-1] and out[-1][-1] in "aeiou":
                out.append(out[-1][-1])
            i += 1
            continue
        two = h[i:i + 2]
        if two in HEPBURN:
            syl = HEPBURN[two]
            i += 2
        elif ch in HEPBURN:
            syl = HEPBURN[ch]
            i += 1
        else:
            return None
        if geminate:
            syl = syl[0] + syl
            geminate = False
        out.append(syl)
    romaji = _collapse_long_vowels("".join(out))
    if not romaji:
        return None
    return romaji.capitalize()


# Suffix type is decided by the KANJI label (unambiguous), not the kana — the
# kana suffix じんぐう alone can't tell 明治/神宮 (Meiji Jingū) from 天神/宮
# (Tenjin-gū). The kana then supplies the stem reading. Most specific kanji
# first: 大神宮 before 神宮, 神社 before 社, 大社 before 社.
#   style "space" -> "<Stem> <word>"; "gu" -> "<Stem>-gu Shrine";
#   "sha" -> "<Stem>-sha Shrine"; "skip" -> deterministically ambiguous, defer.
# Each entry: (kanji_suffix, kana_suffix, english_word, alias_word, style).
_SUFFIXES = [
    ("大神宮", "だいじんぐう", "Daijingu", None, "space"),
    ("大神社", "だいじんじゃ", "Daijinja", None, "space"),
    ("神宮", "じんぐう", None, None, "skip"),       # ambiguous stem boundary -> Stage 4
    ("神社", "じんじゃ", "Shrine", None, "space"),
    ("大社", "たいしゃ", "Grand Shrine", "Taisha", "space"),
    ("宮", "ぐう", "Shrine", None, "gu"),
    ("社", "しゃ", "Shrine", None, "sha"),
]


def label_for(ja: str, kana: str) -> Optional[LabelResult]:
    """Build the English label (+ optional alias) for a shrine from its Japanese
    label and kana reading. The kanji label picks the shrine-type suffix; the
    kana supplies the romanized stem. Returns None — deferring to a later
    pipeline stage — when the suffix is unknown or ambiguous, the kana reading
    doesn't carry the expected suffix, the stem is empty, or it can't be
    confidently romanized."""
    ja = (ja or "").strip()
    h = katakana_to_hiragana((kana or "").strip())
    for kanji_suf, kana_suf, word, alias_word, style in _SUFFIXES:
        if not ja.endswith(kanji_suf):
            continue
        if style == "skip":
            return None
        if not h.endswith(kana_suf):
            return None  # reading doesn't match the kanji suffix -> unreliable
        stem_kana = h[: -len(kana_suf)]
        if not stem_kana:
            return None
        stem = romanize(stem_kana)
        if stem is None:
            return None
        if style == "space":
            label = f"{stem} {word}"
        elif style == "gu":
            label = f"{stem}-gu {word}"
        else:  # "sha"
            label = f"{stem}-sha {word}"
        alias = f"{stem} {alias_word}" if alias_word else None
        return LabelResult(label=label, alias=alias)
    return None
