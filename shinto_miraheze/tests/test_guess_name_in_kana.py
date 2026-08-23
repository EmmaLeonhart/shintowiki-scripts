"""The kana guesser: what it gets right, and the shape of what it gets wrong.

Emma chose the full kana-from-jawiki build on 2026-08-23, guessing included. This pins
the parts that are deterministic. The accuracy itself is NOT pinned here — it is measured
against real data by `guess_name_in_kana.py --measure`, which needs the network.

Measured 2026-08-23 against the 342 readings already extracted from articles:
**47.7% exact, 0% close, 52.3% wrong.** `close` being zero is the important half — the
failures are not long-vowel or small-kana spelling slips, they are different words:

    江島神社   えのしま  guessed えじま
    三吉神社   みよし    guessed さんきち
    一宮神社   いっく    guessed いちのみや

which is the irregular-reading class that makes shrine names hard in the first place.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from guess_name_in_kana import HIRAGANA, _flat, guess, measure, split_suffix  # noqa: E402


# --- the suffix table is the part that must never regress -------------------

def test_longest_suffix_wins():
    """神宮 must not be read as 宮, and 大神宮 must not be read as 神宮."""
    assert split_suffix("伊勢大神宮") == ("伊勢", "だいじんぐう")
    assert split_suffix("熱田神宮") == ("熱田", "じんぐう")
    assert split_suffix("出雲大社") == ("出雲", "たいしゃ")
    assert split_suffix("三芳野神社") == ("三芳野", "じんじゃ")


def test_a_name_that_is_only_a_suffix_still_splits():
    assert split_suffix("神社") == ("", "じんじゃ")


def test_a_name_with_no_known_suffix_is_left_whole():
    assert split_suffix("鹿島") == ("鹿島", "")


# --- the suffix is why a bare converter is not enough ------------------------

def test_the_suffix_bug_a_bare_converter_has():
    """pykakasi reads 三芳野神社 as みよしのがみしゃ — 野神 / 社. The whole reason the
    suffix comes from a table."""
    assert guess("三芳野神社") == "みよしのじんじゃ"


@pytest.mark.parametrize("name,expected", [
    ("出雲大社", "いずもたいしゃ"),
    ("富士崎八幡宮", "ふじさきはちまんぐう"),
])
def test_known_good_guesses(name, expected):
    assert guess(name) == expected


# --- refusing is a valid answer ---------------------------------------------

def test_a_guess_containing_kanji_is_refused_not_returned_partial():
    """A reading with a stray kanji in it is not a reading. P1814 wants a clean modern
    one, so the function returns None rather than something half-converted."""
    out = guess("岡山神社 (高雄州)")
    assert out is None or all(ch in HIRAGANA for ch in out)


def test_empty_name_guesses_nothing():
    assert guess("") is None


# --- the measurement harness itself -----------------------------------------

def test_measure_separates_exact_close_and_wrong():
    exact, close, wrong, misses = measure([
        ("出雲大社", "いずもたいしゃ"),        # exact
        ("三芳野神社", "みよしのじんじゃー"),   # close: long-vowel only
        ("江島神社", "えのしまじんじゃ"),      # wrong: えじま
    ])
    assert (exact, close, wrong) == (1, 1, 1)
    assert misses[0][0] == "江島神社"


def test_flat_ignores_only_spelling_not_words():
    assert _flat("みよしー") == _flat("みよし")
    assert _flat("えのしま") != _flat("えじま")
