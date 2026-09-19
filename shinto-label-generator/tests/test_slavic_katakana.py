"""Polish and Czech/Slovak into katakana, and the English guard Poland forced.

Two more of the five families Emma asked for on 2026-09-19 ("All of them, French
included"): Polish is 748 of the 6,627 refused, Czech + Slovak 289.

⭐ **The more important half of this file is `_ENGLISH_CONTENT`.** Stage 1's
labels for Poland are mostly ENGLISH descriptions of Polish churches, so the
moment `pl` existed they were read with Polish rules:

    Blessed Jerzy Popiełuszko chapel   ->  ブレスセト・イェジ・ポピエウシュコ
    Roman catholic church, Trebišov    ->  ロマン・ツァトホリツ
    Bar Confederation chapel           ->  バル・ツォンフェデラティオン
    Ćmielów Castle                     ->  ツァストレ
    Saint Heribert of Cologne          ->  ツォログネ

Every one is a confident wrong reading of a word whose meaning we know, which is
the failure `romance_katakana.rules_for_country` was written to refuse.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import plain_latin_katakana as p  # noqa: E402
import religious_building_morphemes as m  # noqa: E402

CHURCH = "Q16970"
CHAPEL = "Q108325"


def pl(word):
    return p.to_katakana(word, "pl")


def cs(word):
    return p.to_katakana(word, "cs")


# --------------------------------------------------------------------------
# Polish
# --------------------------------------------------------------------------
def test_l_stroke_is_w_and_w_is_v():
    """⛔ They collide. `Łódź` became `wudź` and the `w -> v` rule one pass later
    turned it into ヴジュ — a different town from ウチ."""
    assert pl("Łódź") == "ウチ"
    assert pl("Michała") == "ミハワ"
    assert pl("Warszawa") == "ヴァルシャヴァ"


def test_nasal_vowels():
    assert pl("Częstochowa") == "チェンストホヴァ"
    assert pl("Świętych") == "シュヴィエンティフ"


def test_a_palatal_plus_i_plus_vowel_is_one_syllable():
    """`Kościan` is コシチャン, not コシュチアン: the i is the palatalisation
    sign and is not itself a vowel."""
    assert pl("Kościan") == "コシュチャン"
    assert pl("Niepokalanego") == "ニェポカラネゴ"


def test_final_devoicing():
    """The commonest case by far is the -ów of a genitive-plural place name."""
    assert pl("Rzeszów") == "ジェシュフ"
    assert pl("Tczew") == "トチェフ"
    assert pl("Pakosław") == "パコスワフ"


def test_a_final_digraph_devoices_as_a_unit():
    """⛔ `Bydgoszcz` ends in a z that belongs to `cz`, and devoicing it
    letter-wise gave ビドゴシュツス."""
    assert pl("Bydgoszcz") == "ビドゴシュチ"
    assert pl("Żywiec") == "ジヴィエツ"


def test_szcz_beats_sz_and_cz():
    assert pl("Szczecin").startswith("シュチェ")


# --------------------------------------------------------------------------
# Czech / Slovak
# --------------------------------------------------------------------------
def test_the_acutes_are_length():
    """⭐ The reason this is not the `bs` family: Bosnian writes no vowel length
    and Czech writes it on every long vowel."""
    assert cs("Nýrsko") == "ニールスコ"
    assert cs("Istebné") == "イステブネー"


def test_de_te_ne_are_palatals_not_d_plus_ye():
    """České Budějovice is ブジェヨヴィツェ; read as d + ye it was ブドイェ-."""
    assert cs("Budějovice") == "ブジェヨヴィツェ"
    assert cs("Hraběticích") == "フラビェティツィーフ"


def test_ji_is_plain_i():
    """Czech j is /j/, so `ji` is イ — Jihlava イフラヴァ, not イィフラヴァ."""
    assert cs("Jihlava") == "イフラヴァ"
    assert cs("Trojice") == "トロイツェ"


def test_r_hacek_reads_as_a_plain_r():
    """⛔ /r̝/ has no kana at all. ドヴォルザーク for Dvořák is a CONVENTION, and
    a village name has no convention to borrow, so the honest output is the r."""
    assert cs("Dvořák") == "ドヴォラーク"


def test_slovak_o_circumflex_and_a_umlaut_are_not_length():
    """Both were taking a ー from the long-vowel table they do not belong in."""
    assert cs("Najsvätejšej") == "ナイスヴェテイシェイ"
    assert "ー" not in cs("Najsvätejšej")


def test_a_final_affricate_is_chi_not_chu():
    assert cs("Třebíč") == "トレビーチ"


def test_the_bare_affricate_override_is_per_family():
    """⚠ Set globally it broke German: -tsch is a cluster with an audible
    off-glide and Deutsch is ドイチュ."""
    assert p.to_katakana("Deutsch", "de") == "ドイチュ"
    assert p._BARE_YOON_BY_RULES["pl"] == {"ch": "チ"}
    assert "de" not in p._BARE_YOON_BY_RULES


# --------------------------------------------------------------------------
# What each family must refuse
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,rules", [
    ("Jördenstorf", "pl"),     # German
    ("Mulatière", "pl"),       # French
    ("Gradačac", "pl"),        # háček
    ("Łódź", "cs"),            # Polish ł and ogonek-family letters
    ("Straße", "cs"),
    ("Kızıl", "cs"),
])
def test_the_wrong_family_refuses(word, rules):
    assert p.to_katakana(word, rules) is None


# --------------------------------------------------------------------------
# ⭐ The English guard
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,rules", [
    ("Blessed Jerzy Popiełuszko chapel in Kraków", "pl"),
    ("Bar Confederation chapel in Sucha Beskidzka", "pl"),
    ("Ćmielów Castle", "pl"),
    ("Roman catholic church, Trebišov", "cs"),
    ("Saint Heribert of Cologne church in Wodzisław", "pl"),
    ("Chapel of Raczyński family in Dębica", "pl"),
    ("Church of Holy Guardian Angels", "pl"),
])
def test_an_english_content_word_refuses_the_label(label, rules):
    assert m.render(label, CHURCH, "ja", place="X", rules=None,
                    latin_rules=rules) is None


def test_the_label_is_refused_not_the_token():
    """⚠ Dropping the token silently would emit ジェジ・ポピエウシュコ礼拝堂 for a
    chapel the source calls Blessed — less than the source said, which is the
    call `_qualifier_residue` already makes."""
    assert m.transliterate_dedication("Blessed Jerzy Popiełuszko chapel", "ja",
                                      latin_rules="pl") is None
    assert m.transliterate_dedication("Jerzy Popiełuszko chapel", "ja",
                                      latin_rules="pl") is not None


def test_a_polish_name_in_an_english_frame_still_reads():
    """The guard is about English CONTENT words. `church in` is frame, and
    Stanislaus Kostka is exactly what this pipeline is for."""
    assert m.render("Saint Stanislaus Kostka church in Poznań", CHURCH, "ja",
                    place="ポズナン", rules=None, latin_rules="pl",
                    place_en="Poznań") == "ポズナンの聖スタニスラウス・コストカ教会"


# --------------------------------------------------------------------------
# The tables Poland exposed
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,rules,expect", [
    ("Church of Holy Family in Augustów", "pl", "聖家族"),
    ("Divine Mercy church in Łódź", "pl", "神のいつくしみ"),
    ("Zum Guten Hirten", "de", "善き牧者"),
    ("Muttergottes", "de", "神の母"),
    ("Immaculata", "de", "無原罪の御宿り"),
])
def test_a_feast_or_title_is_named_not_read(label, rules, expect):
    out = m.render(label, CHURCH, "ja", place="X", rules=None,
                   latin_rules=rules)
    assert out == "Xの" + expect + "教会"


def test_the_german_weak_genitive_on_an_a_name():
    """Katharinenkirche is Katharina-n-kirche. Stripping the -en leaves
    `katharin`, which is not a name, and 24 items were READ instead of NAMED."""
    assert m.name_key("katharinen") == "katharina"
    assert m.name_key("magdalenen") == "magdalena"
    assert m.name_key("annen") == "anna"


def test_the_genitive_rule_still_does_not_invent_names():
    assert m.name_key("fictitiousen") is None
