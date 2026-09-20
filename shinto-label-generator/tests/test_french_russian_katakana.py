"""French and romanised Russian into katakana — the last two of the five.

⛔ **French is the one the repo had refused on purpose.**
`romance_katakana.rules_for_country` says so in its own docstring: French
orthography is not close to phonemic, and reading it with Italian rules gave
`Chapelle Notre-Dame-de-Pitié de Trouville-sur-Mer` ->
ピーチエ・トロウヴィッレ・スル・メル. Shown exactly that and asked which families
to build, Emma answered ***"All of them, French included"*** on 2026-09-19.

What makes it defensible rather than a guess is that the three hard parts are
handled EXPLICITLY, in an order that took four passes to get right:

  * **Softness before the mute e is dropped.** Softness is caused by the very
    letter the mute-e rule deletes. `Vincent` came out ヴァンク, `Hayange` エアン.
  * **The mute e before the accents are folded.** `é` is not mute, and folding
    first made `Pitié` and `Nativité` end in a droppable e.
  * **The nasal ン on a sentinel.** A nasal is a VOWEL, and its n looked exactly
    like a silent final consonant to the pass that follows: `Jean` was ジェア.

Russian is a different kind of family: it reads a TRANSCRIPTION, not an
orthography. Stage 1 writes Russian names in the English romanisation, so the
digraphs are English conventions for Cyrillic letters.
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


def fr(word):
    return p.to_katakana(word, "fr")


def ru(word):
    return p.to_katakana(word, "ru")


# --------------------------------------------------------------------------
# The three ordering bugs, each of which produced a plausible-looking word
# --------------------------------------------------------------------------
def test_softness_survives_the_mute_e():
    """`Vincent` came out ヴァンク because `ce` had already become a bare c by
    the time the c rule ran; `Hayange` エアン because its -ge had lost its e."""
    assert fr("Vincent") == "ヴァンサン"
    assert fr("Hayange") == "アヤンジュ"
    assert fr("France") == "フランス"


def test_an_accented_final_e_is_not_mute():
    assert fr("Pitié") == "ピティエ"
    assert fr("Nativité") == "ナティヴィテ"


def test_the_nasal_n_is_not_a_silent_final():
    """A nasal is a VOWEL. Letter-wise its n looked like a droppable final and
    `Jean` came back ジェア."""
    assert fr("Jean") == "ジャン"
    assert fr("Rouen") == "ルアン"
    assert fr("Carpentras") == "カルパントラ"


def test_the_mute_e_makes_the_consonant_before_it_sound():
    """`Dame` is ダム and `Sainte` サント. Deleted rather than parked, the m
    nasalised and the t fell silent: ダン and サン."""
    assert fr("Dame") == "ダム"
    assert fr("Sainte") == "サント"


def test_a_nasal_is_not_nasal_before_a_doubled_n():
    """`-ienne` is /jɛn/. Étienne came back エトヤン."""
    assert fr("Étienne") == "エティエン"


def test_a_double_consonant_is_one():
    """French writes two and pronounces one: Chapelle シャペル, Villa ヴィラ.
    Read letter-wise they came back サペルル and ヴィルラ."""
    assert fr("Chapelle") == "シャペル"
    assert fr("Villa") == "ヴィラ"


def test_ch_is_sh_not_ch():
    """⚠ The sentinel restores to `sh`. Restored as `ch` the kana grid read
    Chapelle as チャペル."""
    assert fr("Chapelle").startswith("シャ")


def test_ay_is_only_a_digraph_at_the_end_of_a_syllable():
    """In `Hayange` the y is the onset of the next syllable; folded to e it lost
    the first syllable outright and gave アンジュ."""
    assert fr("Hayange") == "アヤンジュ"
    assert fr("Plouay") == "プルエ"


def test_gn_survives_the_y_vowel_rule():
    """⛔ `_Y_VOWEL` runs after the rules table and read the y of `ny` as the
    vowel /i/: Bourgogne came back ブルゴニ. A lookbehind was tried first and was
    too blunt — it also spared the b of Polish `Bydgoszcz`, whose y IS a vowel."""
    assert fr("Bourgogne") == "ブルゴニュ"
    assert p.to_katakana("Bydgoszcz", "pl") == "ビドゴシュチ"


def test_er_is_e_and_runs_after_the_soft_rules():
    """The g of `Boulanger` is soft BECAUSE of that e; folding first gave
    ブランゲ."""
    assert fr("Boulanger") == "ブランジェ"


def test_a_final_x_is_silent_and_goes_before_x_to_ks():
    """-eux is /ø/. Left to `x -> ks` it produced a k no later pass removes."""
    assert fr("Vaujoyeux") == "ヴォジョユ"
    assert fr("Banneux") == "バヌ"


@pytest.mark.parametrize("word,expect", [
    ("Beauvais", "ボヴェ"),
    ("Trouville", "トルヴィル"),
    ("Mulatière", "ムラティエル"),
])
def test_the_rest_of_emmas_example(word, expect):
    assert fr(word) == expect


# --------------------------------------------------------------------------
# Russian: a transcription, not an orthography
# --------------------------------------------------------------------------
def test_the_adjective_ending_is_long():
    """-sky, -skiy and -skii are all -ский, which Japanese writes long."""
    assert ru("Preobrazhensky") == "プレオブラジェンスキー"
    assert ru("Nikolayevsky").endswith("スキー")


@pytest.mark.parametrize("word,expect", [
    ("Spaso", "スパソ"),
    ("Startsevo", "スタルツェヴォ"),
    ("Shchelkovo", "シュチェルコヴォ"),
    ("Yekaterinburg", "イェカテリンブルグ"),
    ("Sophia", "ソフィア"),
])
def test_the_english_digraphs_map_back_to_cyrillic_letters(word, expect):
    assert ru(word) == expect


def test_a_palatalised_consonant_is_one_syllable():
    """`Lyubov` is Любовь, リュボフ. Read letter-wise it was ルユボヴ."""
    assert ru("Lyubov") == "リュボヴ"


def test_a_soft_sign_is_dropped_not_read():
    assert ru("Yaroslavl'") == ru("Yaroslavl")


def test_any_diacritic_at_all_refuses():
    """A romanised name is plain ASCII by definition, so a diacritic means the
    string is not a transcription and this family has no business reading it."""
    assert ru("Jördenstorf") is None
    assert ru("Mulatière") is None
    assert ru("Gradačac") is None


# --------------------------------------------------------------------------
# The country map, and what each family must refuse
# --------------------------------------------------------------------------
def test_the_five_families_are_wired():
    for country, family in (("Q183", "de"), ("Q40", "de"), ("Q36", "pl"),
                            ("Q213", "cs"), ("Q214", "cs"), ("Q142", "fr"),
                            ("Q31", "fr"), ("Q159", "ru"), ("Q212", "ru")):
        assert p.rules_for_country(country) == family


def test_an_unlisted_country_still_refuses():
    """⚠ The doctrine is unchanged and the countries testing it moved — again.

    2026-09-20: **Q55 Netherlands left this list**, because Emma asked for it by
    name. Shown the measurement (492 of the 1,119 long-tail labels are in the
    local language, 304 of them Dutch) and asked which families to build, she
    answered *"All four — nl, sv, no, da"*. So Dutch is an instruction, not the
    guess this test guards against, and Sweden will leave the same way when `sv`
    is built.

    ⛔ What is NOT allowed to change is the doctrine: unlisted means refuse. The
    two left here are the interesting cases, and they stay refused for a reason
    that is not "nobody has got to them" — Finland is 29 of 36 English-labelled
    and Armenia 48 of 51, so their labels are not in the local language at all
    and belong to the placename path, not to a transliteration family.
    """
    for country in ("Q33", "Q399"):
        assert p.rules_for_country(country) is None


@pytest.mark.parametrize("word,rules", [
    ("Łódź", "fr"), ("Straße", "fr"), ("Gradačac", "fr"),
])
def test_the_wrong_family_refuses(word, rules):
    assert p.to_katakana(word, rules) is None


# --------------------------------------------------------------------------
# Frame words these two exposed
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word", ["séminaire", "couvent", "maison", "rue",
                                  "route", "gymnase", "chambre", "ancienne"])
def test_a_french_common_noun_is_frame_not_a_name(word):
    """`Chapelle du séminaire Saint-Yves` is the seminary chapel, and
    `séminaire` was reaching the name slot as 聖セミネル."""
    assert word in m.TYPE_WORDS


def test_bare_burg_and_orts_are_gone_from_the_type_words():
    """⛔ `_strip_compound_type` matches any tail of 4+ characters, so they ate
    the end of every -burg place name: `Yekaterinburg Synagogue` read
    イェカテリン・シナゴーグ, and Magdeburg, Hamburg and Regensburg were all one
    syllable short.

    ⚠ It cost two labels, both for `Hubertusburg` — a castle whose -burg WAS
    being stripped to reach St Hubert. Two against every -burg place name in the
    corpus is the right trade.
    """
    assert "burg" not in m.TYPE_WORDS
    assert "orts" not in m.TYPE_WORDS
    assert "burgkapelle" in m.TYPE_WORDS
    assert "ortskapelle" in m.TYPE_WORDS
    assert m._strip_compound_type("yekaterinburg") == "yekaterinburg"
    assert m._strip_compound_type("magdeburg") == "magdeburg"
