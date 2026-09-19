"""Mosque labels: translate the generic, transliterate the name.

Emma, 2026-09-18 — `Old Mosque` -> 旧モスク, `Upper Mosque` -> 上モスク,
`Omer Mosque` -> オメル・モスク. Before this, all 245 mosques in the corpus produced
ZERO labels, because `dedication()` is a Christian saint vocabulary and nothing in
it can match a mosque.

⛔ Half of these tests exist for the same reason `test_romance_katakana.py`'s do:
the dangerous failure is not a clumsy reading but a CONFIDENT WRONG one. French,
romanised Arabic, Russian-romanised Tatar and German all sit in this population
and all pass a naive letters-are-legal check.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import plain_latin_katakana as p  # noqa: E402
import religious_building_morphemes as m  # noqa: E402

MOSQUE = "Q32815"


# --------------------------------------------------------------------------
# Emma's own three examples, which are the acceptance test
# --------------------------------------------------------------------------
def test_her_three_examples():
    assert m.render("Old Mosque", MOSQUE, "ja", place="テトヴォ") == "テトヴォの旧モスク"
    assert m.render("Upper Mosque", MOSQUE, "ja", place="テトヴォ") == "テトヴォの上モスク"
    assert m.render("Omer Mosque", MOSQUE, "ja", place="テトヴォ",
                    latin_rules="bs") == "テトヴォのオメル・モスク"


def test_the_two_she_chose_on_the_forks():
    """Friday mosque is translated; a surau keeps its own word (2026-09-19)."""
    assert m.render("Juma Mosque", MOSQUE, "ja", place="スムガイト") == "スムガイトの金曜モスク"
    assert m.render("Juma Mosque", MOSQUE, "ko", place="숨가이트") == "숨가이트의 금요 모스크"
    assert m.render("Surau Bulian", MOSQUE, "ja", place="ジャンビ",
                    latin_rules="ms") == "ジャンビのブリアン・スラウ"


def test_korean_modifiers_are_native_not_sino():
    """Emma picked 옛/새/위/아래/큰 over 구/신/상/하/대."""
    assert m.render("Old Mosque", MOSQUE, "ko", place="비제보") == "비제보의 옛 모스크"
    assert m.render("Great Mosque", MOSQUE, "ko", place="테토보") == "테토보의 큰 모스크"


# --------------------------------------------------------------------------
# The generic-vs-name test
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,modifiers", [
    ("Stara Džamija", ["old"]),
    ("Nova Džamija", ["new"]),
    ("Merkez-Moschee", ["central"]),
    ("Masjid Besar Cipaganti", ["great"]),
    ("Masjid Tuo Sitiung", ["old"]),
    ("Ashaghi Mosque in Buzovna", ["lower"]),
    ("Central New Mosque of Avanos", ["central", "new"]),
])
def test_modifiers_are_recognised_in_their_own_language(label, modifiers):
    assert m.mosque_parse(label)[0] == modifiers


def test_a_name_is_whatever_is_left_over():
    mods, friday, surau, names, saw_type = m.mosque_parse("Omer Mosque")
    assert (mods, friday, surau, names, saw_type) == ([], False, False, ["Omer"], True)


def test_the_type_word_is_recognised_in_every_source_language():
    for label in ("Mosque", "Džamija", "Masjid", "Camii", "Moschee",
                  "Mosquée", "məscidi", "Moské"):
        assert m.mosque_parse(label)[4], label


def test_an_ordinal_disambiguator_is_dropped():
    """Nova Džamija I / II are the same label; the duplicate guard picks one."""
    assert m.mosque_parse("Nova Džamija II")[3] == []


def test_a_one_letter_leftover_is_dropped():
    """The H. of `Masjid H. Bakri` is Haji, and read as フ."""
    assert m.mosque_parse("Masjid H. Bakri")[3] == ["Bakri"]


def test_not_named_as_a_mosque_at_all():
    """P31 says mosque, the label does not. There is no slot for these."""
    for label in ("Nablus", "WikiBanua 2.0", "Donauwörther Straße 165",
                  "Nevşehir Külliyesi"):
        assert not m.mosque_parse(label)[4], label
        assert m.render(label, MOSQUE, "ja", place="X", latin_rules="tr") is None


# --------------------------------------------------------------------------
# Slot order
# --------------------------------------------------------------------------
def test_the_modifier_follows_the_name():
    """⛔ 新アダナ・モスク is a mosque in a place called New Adana. The new mosque
    at Adana is アダナ新モスク — a Japanese prefix attaches to what follows it."""
    assert m.render("Adana New Mosque", MOSQUE, "ja", place="セイハン",
                    latin_rules="tr") == "セイハンのアダナ新モスク"


def test_the_interpunct_only_appears_between_two_katakana_runs():
    assert m._kana_join("オメル", "モスク") == "オメル・モスク"
    assert m._kana_join("オメル", "金曜モスク") == "オメル金曜モスク"
    assert m._kana_join("", "モスク") == "モスク"


def test_a_name_word_that_is_the_place_is_not_repeated():
    assert m.render("Mosque in Pirshagi", MOSQUE, "ja", place="ピルシャギ",
                    latin_rules="tr") == "ピルシャギのモスク"


# --------------------------------------------------------------------------
# zh and ko get the generics and refuse the names
# --------------------------------------------------------------------------
def test_zh_and_ko_get_generics_but_never_a_transliterated_name():
    """A translation of `old` is a translation; a reading of a Macedonian village
    name into hanzi is not a derivation. Same line `romance_katakana` holds."""
    assert m.render("Old Mosque", MOSQUE, "zh", place="泰托沃") == "泰托沃旧清真寺"
    assert m.render("Omer Mosque", MOSQUE, "zh", place="泰托沃",
                    latin_rules="bs") is None
    assert m.render("Omer Mosque", MOSQUE, "ko", place="테토보",
                    latin_rules="bs") is None


def test_a_bare_type_word_still_renders_everywhere():
    """77 of the 245 are the bare word. The place is what makes them unique."""
    assert m.render("Mosque", MOSQUE, "ja", place="デバル") == "デバルのモスク"
    assert m.render("Mosque", MOSQUE, "zh", place="德巴尔") == "德巴尔清真寺"
    assert m.render("Mosque", MOSQUE, "ko", place="데바르") == "데바르의 모스크"


# --------------------------------------------------------------------------
# The transliterator itself
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,rules,kana", [
    # Balkan Latin
    ("Omer", "bs", "オメル"),
    ("Bidževo", "bs", "ビジェヴォ"),
    ("Otišani", "bs", "オティシャニ"),
    ("Gradačac", "bs", "グラダチャツ"),
    ("Vrbanjska", "bs", "ヴルバニスカ"),
    ("Srbinovo", "bs", "スルビノヴォ"),
    # Turkish / Azerbaijani
    ("Ömer", "tr", "オメル"),
    ("Göreme", "tr", "ギョレメ"),
    ("Süleyman", "tr", "スレイマン"),
    ("Büyük", "tr", "ビュユク"),
    ("Kızıl", "tr", "クズル"),
    ("Ağa", "tr", "アー"),
    ("Hasanbey", "tr", "ハサンベイ"),
    ("Saltuk", "tr", "サルトゥク"),
    ("Balaxanı", "tr", "バラハヌ"),
    ("Gazakh", "tr", "ガザフ"),
    # Malay / Indonesian
    ("Cipaganti", "ms", "チパガンティ"),
    ("Mungsolkanas", "ms", "ムンソルカナス"),
    ("Bangis", "ms", "バンギス"),
    ("Sulthan", "ms", "スルタン"),
    ("Taqwa", "ms", "タクワ"),
    ("Baiturrahman", "ms", "バイトゥルラフマン"),
])
def test_readings(word, rules, kana):
    assert p.to_katakana(word, rules) == kana


@pytest.mark.parametrize("word,rules", [
    # Not that orthography — the letters give it away.
    ("Donauwörther", "bs"),
    ("Kaybitsy", "bs"),          # y is not Bosnian
    ("Częstochowa", "tr"),
    ("Achères", "ms"),
    # Not a word at all.
    ("165", "ms"),
    ("2.0", "ms"),
])
def test_refusals(word, rules):
    assert p.to_katakana(word, rules) is None


def test_an_unlisted_country_refuses_rather_than_defaulting():
    """⛔ `romance_katakana.rules_for_country` defaulted to Italian once and read
    French as Italian across 14,000 items. Nothing here defaults."""
    # ⚠ France, Germany, Poland and Russia were the examples here until
    # 2026-09-19, when Emma answered "All of them, French included" and they got
    # rule sets. The doctrine is unchanged and the countries testing it moved.
    assert p.rules_for_country("Q34") is None       # Sweden
    assert p.rules_for_country("Q33") is None       # Finland
    assert p.rules_for_country("Q79") is None       # Egypt
    assert p.rules_for_country(None) is None
    assert p.rules_for_country("Q221") == "bs"      # North Macedonia
    assert p.rules_for_country("Q43") == "tr"       # Turkey
    assert p.rules_for_country("Q252") == "ms"      # Indonesia


def test_a_multiword_name_is_all_or_nothing():
    """A half-transliterated name looks deliberate and is not."""
    assert p.name_to_katakana("Sarı Saltuk", "tr") == "サル・サルトゥク"
    assert p.name_to_katakana("Sarı Rzhavets", "tr") is None


def test_no_romance_lengthening_leaks_in():
    """The whole reason this is not `romance_katakana`: Ömer is オメル, and that
    module would give オーメル."""
    assert "ー" not in p.to_katakana("Omer", "bs")
    assert "ー" not in p.to_katakana("Loke", "bs")


def test_an_english_label_refuses_rather_than_being_read_as_malay():
    """`Brunei International Airport Mosque` came out
    ブルネイ・インテルナティオナル・アイルポルト・モスク. Every letter is legal
    Malay, so only the vocabulary can catch it."""
    assert m.render("Brunei International Airport Mosque", MOSQUE, "ja",
                    place="バンダルスリブガワン", latin_rules="ms") is None
    assert m.render("Police Mosque, Sheikh Zayed City", MOSQUE, "ja",
                    place="X", latin_rules="ms") is None


def test_the_mosque_type_words_stay_out_of_the_global_set():
    """⛔ TYPE_WORDS is consulted for all 22,548 items and matched as a suffix.
    Adding `cami` or `mosk` there would change how 18,148 church labels parse."""
    assert not (m.MOSQUE_TYPE_WORDS - {"mosque", "mosques", "moschee",
                                       "mezquita", "synagogue"}) & m.TYPE_WORDS
