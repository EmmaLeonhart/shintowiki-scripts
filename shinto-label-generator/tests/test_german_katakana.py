"""German into katakana — the largest of the five families Emma asked for.

Emma, 2026-09-19, asked which transliterators to build for the 6,627 religious
buildings still refused at the dedication gate: ***"All of them, French
included."*** German is 3,357 of them (Germany 2,754 + Austria 521 + Switzerland
82) and is the most regular, so it went first.

⛔ Half of these exist because the dangerous failure is not a clumsy reading but a
CONFIDENT WRONG one, and German offers several that look fine from the code:

  * `Jerusalem` and `Jördenstorf` — Emma's own example — both came back **None**,
    because `ye` and `yi` are holes in the bare kana grid and a hole fails the
    whole word.
  * `Salvator` came back ツァルファトル: the s-voicing rule wrote a `z` that
    German's own `z -> ts` rule ate one pass later.
  * `Sachsen` came back ザクセン only after the `chs` rule learned that the s it
    is looking for may already be the voiced-s sentinel.
  * `Hospitalkirche` came back `ho`, because it ends with the German type word
    `spitalkirche` and `_strip_compound_type` returns the longest tail it finds.
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


def de(word):
    return p.to_katakana(word, "de")


# --------------------------------------------------------------------------
# Emma's own example, which is the acceptance test
# --------------------------------------------------------------------------
def test_her_example():
    assert de("Jördenstorf") == "イェルデンストルフ"
    assert m.render("Dorfkirche Jördenstorf", CHURCH, "ja", place="テッセン",
                    rules=None, latin_rules="de") == "テッセンのイェルデンストルフ教会"


def test_ye_and_yi_are_holes_in_the_bare_grid():
    """`_ROWS["y"]` is "ヤ-ユ-ヨ", and a `-` fails the whole word. Both of Emma's
    German examples start with J, which is /j/."""
    assert p._ROWS["y"][1] == "-" and p._ROWS["y"][3] == "-"
    assert de("Jerusalem") == "イェルザレム"
    assert de("Jakob") == "ヤコプ"


# --------------------------------------------------------------------------
# The sentinels, each of which was eaten by a later rule first
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,expect", [
    ("Salvator", "ザルファトル"),      # was ツァルファトル
    ("Rosen", "ロゼン"),               # was ロツェン
    ("Unserer", "ウンゼラー"),         # was ウンツェラー
    ("Häuser", "ホイザー"),            # was ホイツァー
])
def test_s_before_a_vowel_is_z_and_survives_the_z_rule(word, expect):
    assert de(word) == expect


def test_a_doubled_s_stays_voiceless():
    """Straße -> strasse must not come back シュトラゼ."""
    assert de("Straße") == "シュトラッセ"


# --------------------------------------------------------------------------
# ch, which is four rules wearing one spelling
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,expect", [
    ("Bach", "バハ"),            # ach-Laut, echoes the back vowel
    ("Nacht", "ナハト"),
    ("Tochter", "トホター"),
    ("Licht", "リヒト"),         # ich-Laut after a front vowel is always ヒ
    ("Knecht", "クネヒト"),
    ("Kirchberg", "キルヒベルク"),   # the colouring vowel is two consonants back
    ("Achenkirch", "アヘンキルヒ"),
    ("Sachsen", "ザクセン"),     # chs is /ks/
    ("Fuchs", "フクス"),
    ("Christkönig", "クリストケニヒ"),  # no preceding vowel at all: Greek /k/
    ("Deutsch", "ドイチュ"),     # tsch is one affricate and belongs to the table
])
def test_ch(word, expect):
    assert de(word) == expect


# --------------------------------------------------------------------------
# Gemination, which this module had none of before German
# --------------------------------------------------------------------------
def test_obstruents_geminate():
    assert de("Göttingen") == "ゲッティンゲン"
    assert de("Rostock") == "ロストック"


def test_liquids_and_nasals_do_not():
    """⚠ German is not Italian here. Müller is ミュラー, not ミュッレル."""
    assert de("Müller") == "ミュラー"
    assert de("Mannheim") == "マンハイム"


# --------------------------------------------------------------------------
# Umlauts: ö is NOT the Turkish ö
# --------------------------------------------------------------------------
def test_o_umlaut_is_a_plain_e():
    """Köln ケルン, Göttingen ゲッティンゲン. `_pre_turkic_rounded` would have
    given ケョルン — the Turkish rule is a different rule."""
    assert de("Köln") == "ケルン"


def test_u_umlaut_takes_the_small_y_row_only_after_a_host():
    assert de("München") == "ミュンヘン"
    assert de("Übersee").startswith("ウ")


# --------------------------------------------------------------------------
# Final position
# --------------------------------------------------------------------------
def test_auslautverhaertung():
    assert de("Wald") == "ヴァルト"
    assert de("Berg") == "ベルク"


def test_final_ng_is_the_nasal_and_does_not_devoice():
    assert de("Wolfgang") == "ヴォルフガング"


def test_final_ig_is_the_ich_laut():
    assert de("König") == "ケニヒ"


# --------------------------------------------------------------------------
# A bare c, which refused the word outright before
# --------------------------------------------------------------------------
def test_bare_c():
    assert de("Clemens") == "クレメンス"
    assert de("Cäcilia") == "ツェツィリア"


# --------------------------------------------------------------------------
# What German must still refuse
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word", ["Łódź", "Gradačac", "Mulatière", "Kızıl"])
def test_not_german_is_refused(word):
    """The letter set is the cheap half of the test and it is enough for these:
    a háček, a Polish ł, a French grave, a Turkish dotless ı."""
    assert de(word) is None


def test_a_digit_is_refused():
    assert de("Kapelle5") is None


# --------------------------------------------------------------------------
# The tables German exposed
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,expect", [
    ("Christkönig", "王たるキリスト"),
    ("Trinitatiskirche", "至聖三者"),
    ("Mariä Geburt", "生神女誕生"),
    ("Maria Hilf", "扶助者聖マリア"),
    ("Zu unserer Lieben Frau", "聖母"),
    ("Hl. Geist", "聖霊"),
    ("Allerheiligenkapelle", "諸聖人"),
])
def test_a_german_dedication_is_named_not_read(label, expect):
    """⭐ One concept, one Japanese form. `Christkönig` is the dedication the
    table already renders 王たるキリスト; read, it was クリストケニヒ."""
    assert m.render(label, CHURCH, "ja", place="X", rules=None,
                    latin_rules="de") == "Xの" + expect + "教会"


def test_a_german_saint_variant_resolves_to_the_table():
    assert m.NAMES["salvator"] == m.NAMES["salvatore"]
    assert m.NAMES["matthaus"] == m.NAMES["matthew"]


@pytest.mark.parametrize("label", ["Feldkapelle", "Wegekapelle", "Spitalkirche",
                                   "Dorfkapelle", "Gnadenkapelle"])
def test_a_german_compound_type_word_is_not_a_name(label):
    """Each says WHERE or WHAT KIND, not who for. `Feldkapelle` is a field
    chapel and emitted フィエロッツォのフェルド礼拝堂 before this.

    ⚠ NARROWED 2026-09-19. Until Emma ruled "translate the modifier, like the
    mosques", not-a-name meant refused outright. It now means the word goes in
    the MODIFIER slot instead of the name slot — 野礼拝堂, not フェルド礼拝堂.
    The invariant these five were written for is unchanged and is what is
    asserted first; what follows it is the new destination.
    """
    assert m._dedicatee_split(label)[0] == [], "must not be read as a dedicatee"
    out = m.render(label, CHAPEL, "ja", place="X", rules=None, latin_rules="de")
    if m.building_modifiers(label):
        assert out and out.endswith("礼拝堂") and "フェルド" not in out
    else:
        assert out is None, "no modifier to translate either"


def test_the_compound_stems_are_never_added_bare():
    """⛔ `_strip_compound_type` matches any tail of 4+ characters, so a bare
    `feld` would reduce Bielefeld to `biele` and a bare `dorf` Ebersdorf to
    `ebers` — for all 22,548 items."""
    for stem in ("feld", "dorf", "berg", "wege", "spital"):
        assert stem not in m.TYPE_WORDS
    assert m._strip_compound_type("bielefeld") == "bielefeld"
    assert m._strip_compound_type("ebersdorf") == "ebersdorf"


def test_a_mis_strip_falls_through_to_the_shorter_tail():
    """`Hospitalkirche` ends with `spitalkirche` and came back `ho` -> 聖ホ・ヤコブ;
    `Ölbergkapelle` ends with `bergkapelle` and came back `öl`."""
    assert m._strip_compound_type("ölbergkapelle") == "ölberg"
    assert m.render("Hospitalkirche St. Jakob", CHURCH, "ja", place="X",
                    rules=None, latin_rules="de") == "Xの聖ヤコブ教会"


def test_a_generic_title_qualifier_now_reaches_the_non_romance_readers():
    """`qualifier_kana` knew only `romance_katakana`, so a German Marian label
    with a qualifier refused in a country that had a perfectly good rule set."""
    assert m.render("Kapelle Unserer Lieben Frau ob der Brücke", CHAPEL, "ja",
                    place="X", rules=None,
                    latin_rules="de") == "Xのオプ・ブリュッケの聖母礼拝堂"


# --------------------------------------------------------------------------
# The other families are untouched
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,rules,expect", [
    ("Omer", "bs", "オメル"),
    ("Gradačac", "bs", "グラダチャツ"),
    ("Vrbanjska", "bs", "ヴルバニスカ"),
    ("Süleyman", "tr", "スレイマン"),
    ("Saltuk", "tr", "サルトゥク"),
    ("Rzhavets", "tr", None),
])
def test_the_mosque_families_are_unchanged(word, rules, expect):
    assert p.to_katakana(word, rules) == expect
