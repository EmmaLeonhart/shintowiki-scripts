"""
temple_english.py — deterministic kana -> English Buddhist-temple label.

Temple analogue of ``kana_english.py`` (the Stage-1 deterministic step) for
Japanese Buddhist temples (P31=Q5393308, P17=Q17) that have a Japanese label +
kana reading but no English label.

Emma's temple convention (2026-06-23): temples are inconsistent, so PRESERVE the
full Japanese reading — ``"<Stem>-<suffix> Temple"``: the stem, a hyphen, the
suffix romanized **from the kana** (so the actual reading is kept), a space, then
``Temple``:

    寺 read じ    -> "<Stem>-ji Temple"      (誓願寺 せいがんじ  -> Seigan-ji Temple)
    寺 read でら  -> "<Stem>-dera Temple"    (清水寺 きよみずでら -> Kiyomizu-dera Temple)
    寺 read てら  -> "<Stem>-tera Temple"
    院 read いん  -> "<Stem>-in Temple"      (三千院 さんぜんいん -> Sanzen-in Temple)
    庵 read あん  -> "<Stem>-an Temple"
    堂 read どう  -> "<Stem>-do Temple"
    坊 read ぼう  -> "<Stem>-bo Temple"

Brackets: Wikidata labels must not contain bracketed disambiguators (a labelling
error). Strip （）()〔〕 content from BOTH ja and kana before anything else.

Conservative by design (mirrors the shrine version): the ja label must end in a
known temple-suffix kanji AND the kana must end in an accepted reading for that
suffix; the stem must romanize fully and be non-empty. Anything else returns
None, so the temple falls through to a later stage (wiki-title lookup / LLM)
rather than getting a wrong label onto Wikidata. Non-temple items that slipped
into the P31=Q5393308 set (教会 church, 僧伽 sangha, 〇〇派 sect, …) end in
non-temple kanji and so return None.
"""

import re
from dataclasses import dataclass
from typing import Optional

from kana_english import romanize, katakana_to_hiragana

_BRACKETS = re.compile(r"[（(〔][^）)〕]*[）)〕]")


def strip_brackets(s: str) -> str:
    """Remove full-width （）, half-width () and 〔〕 bracketed content."""
    return _BRACKETS.sub("", s).strip()


# kanji suffix -> accepted (kana_reading, english_suffix) pairs.
# Longest / most-specific kana reading first so でら/てら beat じ.
_TEMPLE_SUFFIXES = {
    "寺": [("でら", "dera"), ("てら", "tera"), ("じ", "ji")],
    "院": [("いん", "in")],
    "庵": [("あん", "an")],
    "堂": [("どう", "do"), ("どー", "do")],
    "坊": [("ぼう", "bo"), ("ぼ", "bo")],
}


@dataclass
class LabelResult:
    label: str
    alias: Optional[str] = None


def label_for(ja: str, kana: str) -> Optional[LabelResult]:
    """Build "<Stem>-<suffix> Temple" from a temple's ja label + kana, or None."""
    if not ja or not kana:
        return None
    ja = strip_brackets(ja)
    kana = katakana_to_hiragana(strip_brackets(kana))
    if not ja or not kana:
        return None
    # Generic 寺院 ("jiin", the common noun for a temple) is not a name suffix.
    if ja.endswith("寺院"):
        return None
    pairs = _TEMPLE_SUFFIXES.get(ja[-1])
    if not pairs:
        return None
    for kana_suf, eng_suf in pairs:
        if kana.endswith(kana_suf) and len(kana) > len(kana_suf):
            stem = romanize(kana[: -len(kana_suf)])
            if not stem:
                return None
            return LabelResult(label=f"{stem}-{eng_suf} Temple")
    return None
