"""Dutch into katakana — the first of the four families Emma asked for (2026-09-20).

Asked which of nl/sv/no/da to build for the 492 native-language long-tail
religious buildings, with the measurement in front of her, Emma answered
**"All four — nl, sv, no, da"**. Dutch is the first: 304 of the 492, and the
most regular of them.

⛔ **The compound is why this is tractable.** `kerk` is in **232 of the 304**
labels, glued to the end of a name — Bonifatiuskerk, Zeemanskerk, Fonteinkerk.
Dutch writes compounds solid, so a letter-wise reader walks across the seam
without noticing, and every rule below had to be checked against a real label
rather than against a citation form.

⚠ These assert the READING, not a house style. Where a conventional Japanese
spelling exists it is used as the check — Rotterdam ロッテルダム, Maastricht
マーストリヒト, Scheveningen スヘフェニンゲン, Huis ten Bosch's ハウス and ボス —
because a family that disagrees with the attested form is reading something else.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from plain_latin_katakana import (  # noqa: E402
    to_katakana, rules_for_country, COUNTRY_RULES,
)


def k(word):
    return to_katakana(word, "nl")


# --------------------------------------------------------------------------
# The digraph vowels, which are not the sum of their letters
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,expected", [
    ("Rijn", "ライン"),            # ij = /ɛi/
    ("Hogendijk", "ホゲンダイク"),
    ("Huis", "ハウス"),            # ui, as in Huis ten Bosch ハウステンボス
    ("Oude", "アウデ"),            # ou
    ("Zoutkamp", "ザウトカンプ"),
    ("Fonteinkerk", "フォンタインケルク"),   # ei
    ("Zeemanskerk", "ゼーマンスケルク"),     # ee, doubled = long
    ("Maastricht", "マーストリヒト"),        # aa, and cht
])
def test_digraph_vowels(word, expected):
    assert k(word) == expected


def test_ieuw_is_not_i_plus_eu():
    """⛔ `nieuw` is /iu/ — ニュー since Nieuw Amsterdam. Letter-wise, with `eu`
    winning over `ie`, it came back ニウーウェ."""
    assert k("Nieuwe") == "ニューウェ"


# --------------------------------------------------------------------------
# ⛔ The two that the kana grid itself got wrong
# --------------------------------------------------------------------------
def test_sch_is_two_sounds_and_the_grid_must_not_read_it_as_one():
    """`sch` is s + the fricative. Written as a bare `s` beside an `h`, the grid
    reads `sh` as ONE consonant and Scheveningen came back シェフェニンゲン.
    It is スヘフェニンゲン, which is why the ス is forced explicitly."""
    assert k("Scheveningen") == "スヘフェニンゲン"
    assert k("Schiedam") == "スヒーダム"


def test_final_sch_is_the_fossil_s():
    """Word-final `-sch` is /s/ — Bosch is ボス, which is why Huis ten Bosch is
    ハウステンボス and not ハウステンボスフ."""
    assert k("Bosch") == "ボス"


def test_cht_takes_the_hi_column_not_hu():
    """⛔ `-cht` is everywhere in Dutch placenames. Left to the grid's bare-h
    default it came back ウトレフト and マーストリフト."""
    assert k("Utrecht") == "ウトレヒト"
    assert k("Dordrecht") == "ドルドレヒト"
    assert k("Sliedrecht") == "スリードレヒト"


# --------------------------------------------------------------------------
# ⛔ qu, and the rule-ordering bug it exposed in TWO families
# --------------------------------------------------------------------------
def test_qu_survives_the_vowel_digraphs():
    """`Quirinuskerk` was the ONE word of the 304 this family could not read.
    `qui` contains `ui`, the vowel rule fired inside it, and what was left was a
    bare `q` nothing can read: quirinuskerk -> qaurinuskerk -> refused. So `qu`
    resolves before the vowel digraphs."""
    assert k("Quirinuskerk") == "クウィリヌスケルク"


def test_german_qu_was_eaten_by_its_own_v_rule():
    """⚠ Found in the German family while building this one, not introduced by
    it: German wrote `qu -> kv`, and its own `v -> f` two rules later turned that
    into `kf`. Quelle came back クフェレ. `kw` survives that rule and German's
    `w -> v` restores it. 2 labels in the corpus are affected, both `St. Quirin`."""
    assert to_katakana("Quelle", "de") == "クヴェレ"
    assert to_katakana("Quirin", "de") == "クヴィリン"


def test_the_german_family_is_otherwise_untouched():
    """A fix inside a shared table is a change to every caller of it."""
    assert to_katakana("Göttingen", "de") == "ゲッティンゲン"
    assert to_katakana("München", "de") == "ミュンヘン"
    assert to_katakana("Clemens", "de") == "クレメンス"
    assert to_katakana("Kirche", "de") == "キルヘ"


# --------------------------------------------------------------------------
# Consonants: what Dutch does NOT share with German
# --------------------------------------------------------------------------
def test_w_is_the_wa_row_not_german_v():
    """German maps `w -> v`; Dutch /ʋ/ is the ワ row. Willem is ウィレム."""
    assert k("Willem") == "ウィレム"


def test_initial_v_devoices():
    """Japanese has written Dutch initial v as フ for centuries: Van Gogh ファン,
    Vermeer フェルメール."""
    assert k("Vermeer") == "フェルメール"


def test_doubled_sonorants_do_not_geminate_but_obstruents_do():
    """⚠ Dutch doubles a consonant to mark the vowel before it SHORT. For an
    obstruent Japanese writes ッ; for l/m/n/r there is nothing to write, and left
    alone Willem came back ウィルレム."""
    assert k("Bakker") == "バッケル"
    assert k("Rotterdam") == "ロッテルダム"
    assert k("Willem") == "ウィレム"


def test_trema_is_a_syllable_break_not_a_vowel_change():
    """Dutch ë ï do not change the vowel — they say it starts a new syllable,
    which reading the vowels separately already does."""
    assert k("Belgie") == k("België")


# --------------------------------------------------------------------------
# Refusals — the point of the module
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word", [
    "Kraków",        # Polish
    "Třebíč",        # Czech
    "Gradačac",      # Bosnian
    "Kızıl",         # Turkish
    "Pitié",         # French
    "Straße",        # German
])
def test_a_word_that_is_not_dutch_is_refused(word):
    assert k(word) is None


def test_the_country_map_gained_only_the_netherlands():
    """⚠ Belgium stays on `fr` and that is deliberate: COUNTRY_RULES is one
    family per country and the Belgian labels in this corpus are French. The
    same limit leaves a handful of French labels in Switzerland refused rather
    than mis-read, which is the correct outcome."""
    assert rules_for_country("Q55") == "nl"
    assert rules_for_country("Q31") == "fr"     # Belgium
    assert COUNTRY_RULES.get("Q183") == "de"    # Germany, unchanged


# --------------------------------------------------------------------------
# The corpus itself
# --------------------------------------------------------------------------
def test_every_dutch_word_in_the_corpus_is_readable():
    """⛔ The measurement this family exists for, and it is run rather than
    quoted: all 304 native-language Netherlands labels, word by word.

    It was 303/304 until `qu` moved ahead of the vowel digraphs.
    """
    import json
    import re
    import generate_religious_building_multilang as G
    import religious_building_morphemes as m
    with open(G.CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)["items"]
    english = re.compile(
        r"\b(church|chapel|cathedral|monastery|synagogue|mosque|basilica|"
        r"abbey|convent|temple|hospital|memorial|monument)\b", re.I)
    unreadable, total = [], 0
    for qid, label in G.source_labels():
        meta = cache.get(qid) or {}
        if (meta.get("p17") != "Q55" or m.is_category_shaped(label)
                or not G.building_type(meta, m.TYPES) or english.search(label)):
            continue
        total += 1
        for word in re.split(r"[\s,\-–'’/()\.]+", label):
            if word and not any(c.isdigit() for c in word) and k(word) is None:
                unreadable.append((label, word))
    assert total > 250, "the Dutch corpus has shrunk; re-measure before trusting this"
    assert not unreadable, "unreadable Dutch words: %s" % unreadable[:10]
