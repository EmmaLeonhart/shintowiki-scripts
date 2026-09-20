"""Buildings named after nothing but a denomination or a setting (2026-09-19).

Emma, shown that 790 German-family labels name no dedicatee at all and only 68
distinct texts between them: ***translate the modifier, like the mosques.*** That
is her 2026-09-18 mosque call — "translate the generic, transliterate the name",
`Old Mosque` → 旧モスク — applied where there is no name at all, so the whole
label is place + modifier + type.

⭐ **A translation reaches all three languages**, unlike the transliteration
fallback. ja 9,114 → 9,552, zh 5,442 → 5,937, ko 2,065 → 2,170.

⛔ `evangelisch` is 福音主義 and `protestantisch` is プロテスタント — her call the
same day. They mean the same thing in German and the corpus keeps them apart, so
one word for both would give a town holding one of each a single label and the
duplicate guard would drop the second.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402

CHURCH = "Q16970"
CHAPEL = "Q108325"


def r(label, lang="ja", p31=CHURCH, place="X"):
    return m.render(label, p31, lang, place=place, rules=None, latin_rules="de")


# --------------------------------------------------------------------------
# Emma's two calls
# --------------------------------------------------------------------------
def test_the_two_words_she_kept_apart():
    assert r("Evangelische Kirche") == "Xの福音主義教会"
    assert r("Protestantische Kirche") == "Xのプロテスタント教会"
    assert r("Evangelische Kirche") != r("Protestantische Kirche")


def test_it_is_a_translation_so_all_three_languages_get_it():
    """The transliteration fallback is ja-only because a reading has no route to
    hanzi or hangul. A translation does."""
    assert r("Evangelische Kirche", "zh") == "X福音主义教堂"
    assert r("Evangelische Kirche", "ko") == "X의 복음주의 교회"
    assert r("Neuapostolische Kirche", "zh") == "X新使徒教堂"


@pytest.mark.parametrize("label,expect", [
    ("Neuapostolische Kirche", "新使徒"),
    ("Friedhofskapelle", "墓地"),
    ("Wegkapelle", "道端"),
    ("Dorfkirche", "村"),
    ("Feldkapelle", "野"),
    ("Klosterkirche", "修道院"),
    ("Kriegergedächtniskapelle", "戦没者記念"),
])
def test_the_measured_vocabulary(label, expect):
    out = r(label, p31=CHAPEL)
    assert out and expect in out


def test_a_compound_denomination_keeps_both_parts():
    assert r("Evangelisch-reformierte Kirche") == "Xの福音主義改革派教会"
    assert r("Evangelische Pfarrkirche") == "Xの福音主義教区教会"


def test_longest_stem_wins():
    """⛔ `altkatholisch` must beat `katholisch`, and `neuapostolisch` must not be
    read as `apostel`."""
    assert r("Altkatholische Kirche") == "Xの古カトリック教会"
    assert "使徒" in r("Neuapostolische Kirche")
    assert r("Neuapostolische Kirche") != r("Apostelkirche")


def test_old_and_new_come_from_the_mosque_table():
    """⚠ One vocabulary for one concept — `GENERIC_MODIFIERS` already had 旧 and
    新 in all three languages for the mosques."""
    out = r("Alte Synagoge", p31="Q34627")
    assert out and out.startswith("Xの旧")
    assert m.GENERIC_MODIFIERS["old"]["ja"] == "旧"


# --------------------------------------------------------------------------
# ⛔ Only when the label names nothing else
# --------------------------------------------------------------------------
def test_a_named_building_is_not_given_a_generic_label():
    """⛔ Without this it fired for zh and ko on every item whose name ja had
    just transliterated: `Evangelische Kirche Blankenbach` came out
    ゾントラのブランケンバハ教会 in ja and 松特拉福音主义教堂 in zh — the same
    building described two different ways, with zh dropping the one word that
    distinguishes it. 814 zh lines appeared that way, 172 promptly colliding."""
    assert m.render_generic("Evangelische Kirche Blankenbach", CHURCH, "ja",
                            "X") is None
    ja = r("Evangelische Kirche Blankenbach")
    zh = r("Evangelische Kirche Blankenbach", "zh")
    assert ja and "ブランケンバハ" in ja
    assert zh is None, "zh has no route to a German place name and must refuse"


def test_a_dedication_still_wins():
    assert r("Evangelische Kirche St. Martin").endswith("聖マルティヌス教会")


# --------------------------------------------------------------------------
# ⛔ A bare type word is still not a name
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label", ["Kapelle", "Kirche", "Synagoge", "Basilika"])
def test_a_bare_type_word_is_refused(label):
    """A bare `Kapelle` is not named after its setting either — it is simply not
    named, which is the line `render` has always held. 113 of the 790 are this
    shape and they stay refused."""
    assert r(label) is None
    assert m.building_modifiers(label) == []


def test_the_modifier_is_read_off_the_raw_label():
    """Every one of these words is in TYPE_WORDS — that is exactly why the item
    has no name token and reaches this function at all, so the parsed tokens are
    the wrong thing to look at."""
    assert m._dedicatee_split("Friedhofskapelle")[0] == []
    assert m.building_modifiers("Friedhofskapelle") == ["friedhof"]


def test_hof_is_flagged_as_mine_not_hers():
    """⚠ `hof` as 農場 is my call, the way the zh cell for surau was. Recorded in
    the module so the next reader knows which cells carry her ruling."""
    assert "農場" == m.BUILDING_MODIFIERS["hof"]["ja"]
    assert "MINE, not hers" in m.__doc__ or "MINE, not hers" in open(
        os.path.join(HERE, "religious_building_morphemes.py"),
        encoding="utf-8").read()


def test_every_modifier_covers_all_three_languages():
    for key, row in m.BUILDING_MODIFIERS.items():
        assert set(row) == {"ja", "zh", "ko"}, key
        assert all(row[lg].strip() for lg in row), key
