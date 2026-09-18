"""Romance place names into katakana — and, more importantly, what it refuses.

The corpus's remaining refused qualifiers are localities ("Madonna del Pero",
"Madonna di Campiglio"), so finishing them means transliterating. Romance
orthography is close to phonemic, which makes that derivable rather than guessed.

⛔ The dangerous failure is not a clumsy reading, it is a CONFIDENT WRONG one. The
same corpus carries Polish, Czech, German and Russian place names, and the first
version read `Rzhavets` as Italian and returned ルツァヴェツ. Half these tests
exist to keep that refusing.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import romance_katakana as r  # noqa: E402


@pytest.mark.parametrize("word,expect", [
    ("Pero", "ペロ"),
    ("Loreto", "ロレト"),
    ("Milano", "ミラノ"),
    ("Assisi", "アシシ"),
    ("Genova", "ジェノヴァ"),
    ("Firenze", "フィレンツェ"),      # z -> ts
    ("Giovanni", "ジョヴァンニ"),      # gio -> jo, geminate nn
    ("Bologna", "ボロニャ"),          # gn -> ny
    ("Chiesa", "キエサ"),             # ch -> hard k
    ("Coimbra", "コインブラ"),         # m before b closes the syllable
    ("Umbria", "ウンブリア"),          # three consonants IS Romance
])
def test_it_reads_romance_names(word, expect):
    assert r.to_katakana(word) == expect


@pytest.mark.parametrize("word,expect", [
    # Each of these was wrong in a way worth pinning.
    ("Campiglio", "カンピリョ"),   # gli -> ry, and m before p is ン not ム
    ("Cardello", "カルデッロ"),    # Italian geminate, NOT the Spanish ll -> y
    ("Brescia", "ブレシャ"),       # the silent-h strip used to eat this sh
    ("Pescia", "ペシャ"),
    ("Sondrio", "ソンドリオ"),     # bare d is ド, not the archaic ヅ
    ("Trento", "トレント"),        # bare t is ト, not ツ
])
def test_the_cases_that_were_wrong(word, expect):
    assert r.to_katakana(word) == expect


@pytest.mark.parametrize("word", [
    "Rzhavets",      # Russian -- returned ルツァヴェツ before the shape gate
    "Bąkowa",        # Polish
    "Zgierz",        # Polish, initial cluster Romance does not permit
    "Kraków",        # k and w
    "Przemyśl",
    "Szczecin",
    "Welschenrohr",  # German
    "Mümliswil",
])
def test_it_refuses_what_is_not_romance(word):
    assert r.to_katakana(word) is None, (
        f"{word} was read with Romance rules; a confident wrong reading is the "
        f"failure this module exists to avoid"
    )


def test_the_shape_gate_agrees_with_the_reader():
    for w in ("Milano", "Campiglio", "Umbria"):
        assert r.is_romance_shaped(w)
    for w in ("Rzhavets", "Kraków", "Szczecin"):
        assert not r.is_romance_shaped(w)


def test_a_multi_word_place_joins_with_nakaguro():
    assert r.place_to_katakana("Santa Maria") == "サンタ・マリア"


def test_one_unreadable_word_refuses_the_whole_phrase():
    """A half-transliterated name looks deliberate, which is worse than none."""
    assert r.place_to_katakana("Santa Maria Rzhavets") is None


def test_empty_input_is_refused():
    assert r.to_katakana("") is None
    assert r.place_to_katakana("") is None
    assert r.place_to_katakana("   ") is None


def test_accents_are_dropped_not_rejected():
    """Romance accents mark stress, which kana does not write."""
    assert r.to_katakana("Tábuas") == r.to_katakana("Tabuas") == "タブアス"
