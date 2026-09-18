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
    ("Pero", "ペーロ"),
    ("Loreto", "ロレート"),
    ("Milano", "ミラーノ"),
    ("Assisi", "アッシーシ"),
    ("Genova", "ジェノーヴァ"),
    ("Firenze", "フィレンツェ"),      # z -> ts
    ("Giovanni", "ジョヴァンニ"),      # gio -> jo, geminate nn
    ("Bologna", "ボローニャ"),          # gn -> ny
    ("Chiesa", "キエーサ"),             # ch -> hard k
    ("Coimbra", "コインブラ"),         # m before b closes the syllable
    ("Umbria", "ウンブリア"),          # three consonants IS Romance
])
def test_it_reads_romance_names(word, expect):
    assert r.to_katakana(word) == expect


@pytest.mark.parametrize("word,expect", [
    # Each of these was wrong in a way worth pinning.
    ("Campiglio", "カンピーリョ"),   # gli -> ry, and m before p is ン not ム
    ("Cardello", "カルデッロ"),    # Italian geminate, NOT the Spanish ll -> y
    ("Brescia", "ブレーシャ"),       # the silent-h strip used to eat this sh
    ("Pescia", "ペーシャ"),
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
    assert r.place_to_katakana("Santa Maria") == "サンタ・マーリア"


def test_one_unreadable_word_refuses_the_whole_phrase():
    """A half-transliterated name looks deliberate, which is worse than none."""
    assert r.place_to_katakana("Santa Maria Rzhavets") is None


def test_empty_input_is_refused():
    assert r.to_katakana("") is None
    assert r.place_to_katakana("") is None
    assert r.place_to_katakana("   ") is None


def test_an_accent_places_the_stress():
    """This asserted that accents were merely DROPPED, which was true when the
    output had no long vowels at all. Now a written accent marks irregular
    stress and moves the ー, which is the whole point of reading it."""
    assert r.to_katakana("Tábuas") == "ターブアス"
    assert r.to_katakana("Città") == "チッタ"   # final stress, closed syllable


# --------------------------------------------------------------------------
# Vowel length — added 2026-09-18 after checking against real ja labels
# --------------------------------------------------------------------------

@pytest.mark.parametrize("word,expect", [
    ("Fiore", "フィオーレ"),     # サンタ・マリア・デル・フィオーレ大聖堂 on Wikidata
    ("Salute", "サルーテ"),      # サンタ・マリア・デッラ・サルーテ聖堂
    ("Loreto", "ロレート"),
    ("Bologna", "ボローニャ"),
    ("Roma", "ローマ"),
])
def test_the_stressed_open_syllable_is_long(word, expect):
    """The first version produced NO long vowels at all, while every real ja
    church label has them. Romance stress is penultimate unless written
    otherwise, and Japanese writes a stressed open syllable long."""
    assert r.to_katakana(word) == expect


@pytest.mark.parametrize("word,expect", [
    ("Cardello", "カルデッロ"),   # closed by the geminate
    ("Trento", "トレント"),       # closed by ン
])
def test_a_closed_syllable_takes_no_long_vowel(word, expect):
    assert r.to_katakana(word) == expect


@pytest.mark.parametrize("word,expect", [
    # Both were mangled by a rule running in the wrong order.
    ("Città", "チッタ"),     # the leftover c->k ate the ch the soft-c rule made
    ("Nossa", "ノッサ"),     # ss is a geminate; collapsing it lost the small tsu
])
def test_the_ordering_bugs_stay_fixed(word, expect):
    assert r.to_katakana(word) == expect


def test_a_geminate_survives():
    for w in ("Assisi", "Nossa", "Cardello"):
        assert "ッ" in r.to_katakana(w), w


# --------------------------------------------------------------------------
# Per-language rules, chosen from P17
# --------------------------------------------------------------------------

def test_the_country_picks_the_rule_set():
    assert r.rules_for_country("Q38") == "it"     # Italy
    assert r.rules_for_country("Q45") == "pt"     # Portugal
    assert r.rules_for_country("Q155") == "pt"    # Brazil
    assert r.rules_for_country("Q29") == "es"     # Spain
    assert r.rules_for_country("Q414") == "es"    # Argentina
    assert r.rules_for_country("Q183") is None    # Germany -> refuse, not a default


@pytest.mark.parametrize("word,rules,expect", [
    # ⛔ The case that proved "Italian wins" was backwards: Italian ce is an
    # affricate, Portuguese and Spanish ce is /s/.
    ("Conceição", "pt", "コンセイーサン"),
    ("Conceição", "it", "コンチェイーサン"),
])
def test_soft_c_differs_by_language(word, rules, expect):
    assert r.to_katakana(word, rules) == expect


def test_spanish_ll_is_y_and_italian_ll_is_a_geminate():
    """The same two letters, opposite readings. Applying one rule to both was
    the bug: Cardello came out カルデヨ under Spanish rules."""
    assert r.to_katakana("Sevilla", "es") == "セヴィーヤ"
    assert r.to_katakana("Cardello", "it") == "カルデッロ"


def test_the_default_is_still_italian():
    assert r.to_katakana("Cardello") == r.to_katakana("Cardello", "it")


def test_an_unlisted_country_refuses_rather_than_defaulting():
    """⛔ This returned Italian for anything unlisted, which on the real corpus
    meant 14,000+ items -- and it leaked: French passes the Romance shape gate,
    so Notre-Dame-de-Pitié de Trouville-sur-Mer came out
    ピーチエ・トロウヴィッレ・スル・メル. Same failure as reading Rzhavets as
    Italian, just harder to see because the letters look plausible."""
    for qid in ("Q142", "Q183", "Q36", "Q159", "Q16"):   # FR, DE, PL, RU, CA
        assert r.rules_for_country(qid) is None, qid
    for qid, expect in (("Q38", "it"), ("Q45", "pt"), ("Q29", "es")):
        assert r.rules_for_country(qid) == expect
