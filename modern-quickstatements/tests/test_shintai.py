"""神体 (shintai) import — P825 + P3831=Q327532 (Emma 2026-07-10).

Every fixture is real text from a live jawiki shrine infobox. The two traps:
`（[[神体山]]）` is a class annotation rather than the shintai, and a piped link's
target is often the containing article.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_shintai_quickstatements as sh  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


# ─────────────────── the class-annotation trap ───────────────────

@pytest.mark.parametrize("field,target", [
    ("[[弥彦山]]（[[神体山]]）", "弥彦山"),                      # 彌彦神社
    ("[[立山]]（[[神体山]]）", "立山"),                          # 雄山神社
    ("[[鳥海山]]（[[神体山]]）", "鳥海山"),                      # 鳥海山大物忌神社
    ("[[猿投山]]（[[神体山]]）", "猿投山"),                      # 猿投神社
])
def test_the_class_annotation_is_not_the_shintai(field, target):
    """36 of 45 raw link targets are the word 神体山. Reading links naively would
    emit `<shrine>|P825|神体山` over and over."""
    assert sh.extract_shintai(field) == target


def test_a_class_word_alone_yields_nothing():
    assert sh.extract_shintai("（[[神体山]]）") is None


@pytest.mark.parametrize("word", sorted(sh.CLASS_WORDS))
def test_every_class_word_is_excluded(word):
    assert sh.extract_shintai("[[{}]]".format(word)) is None


# ─────────────────── the piped-target trap ───────────────────

def test_a_disambiguator_on_the_target_is_fine():
    """厳島神社: [[弥山 (広島県)|弥山]] — display drops only the disambiguator."""
    assert sh.extract_shintai("[[弥山 (広島県)|弥山]]（[[神体山]]）") == "弥山 (広島県)"


def test_a_long_disambiguator_is_fine():
    field = "[[本宮山 (岡崎市・豊川市・新城市)|本宮山]]（[[神体山]]）"
    assert sh.extract_shintai(field) == "本宮山 (岡崎市・豊川市・新城市)"


def test_a_topic_disambiguator_is_fine():
    field = "[[富士山 (代表的なトピック)|富士山]]（[[神体山]]）"
    assert sh.extract_shintai(field) == "富士山 (代表的なトピック)"


def test_a_section_link_to_a_district_is_refused():
    """賀茂別雷神社: [[柊野#名所・旧跡|神山]] — 柊野 is a district, not the shintai."""
    assert sh.extract_shintai("[[柊野#名所・旧跡|神山]]（[[神体山]]）") is None


def test_a_range_targeted_by_a_peak_is_refused():
    """春日大社: [[春日山 (奈良県)|御蓋山]] — target is the range, display the peak."""
    assert sh.extract_shintai("[[春日山 (奈良県)|御蓋山]]（[[神体山]]）") is None


def test_a_variant_spelling_display_is_refused():
    """熱田神宮: [[天叢雲剣|草薙神剣（草薙剣）]] — display is not the target."""
    assert sh.extract_shintai("[[天叢雲剣|草薙神剣（草薙剣）]]") is None


def test_a_bare_link_is_accepted():
    assert sh.extract_shintai("[[戸隠山]]") == "戸隠山"          # 戸隠神社
    assert sh.extract_shintai("[[八咫鏡]]") == "八咫鏡"          # 皇大神宮
    assert sh.extract_shintai("[[布都御魂剣]]") == "布都御魂剣"   # 石上神宮


# ─────────────────── refusals ───────────────────

def test_multiple_segments_are_refused():
    """宗像大社 names a different object for each of its three shrines."""
    field = "[[御霊代]]は<br/>青玉（沖津宮）<br/>紫玉（中津宮）<br/>八咫鏡（邊津宮）"
    assert sh.extract_shintai(field) is None


def test_two_different_links_are_refused():
    assert sh.extract_shintai("[[八咫鏡]]と[[草薙剣]]") is None


@pytest.mark.parametrize("field", ["", None, "   ", "御室山", "本殿内殿内陣の土間", "巨大な男根"])
def test_unlinked_or_empty_values_are_refused(field):
    assert sh.extract_shintai(field) is None


# ─────────────────── line shape ───────────────────

URL = "https://ja.wikipedia.org/wiki/X"


def test_line_shape():
    assert sh.qs_line("Q1", "Q2", URL) == 'Q1|P825|Q2|P3831|Q327532|S4656|"%s"' % URL


def test_the_role_qid_is_the_verified_one():
    """Q327532 = shintai, 'objects worshipped at or near Shinto shrines'."""
    assert sh.SHINTAI == "Q327532"
    assert sh.P_DEDICATED == "P825"
    assert sh.P_ROLE == "P3831"


def test_it_uses_the_same_property_as_the_honzon_import():
    """Internal consistency is why P825 was chosen: 本尊 is the temple's analogue."""
    import generate_honzon_quickstatements as honzon
    assert "P825" in honzon.__doc__
    assert sh.P_DEDICATED == "P825"


def test_no_line_is_a_removal():
    assert not sh.qs_line("Q1", "Q2", URL).startswith("-")


# ─────────────────── the daily editor can execute it ───────────────────

def test_the_daily_editor_parses_the_line():
    p = dde.parse_qs_line(sh.qs_line("Q42", "Q39231", URL))
    assert p["entity"] == "Q42" and p["property"] == "P825"
    assert p["value"]["value"]["id"] == "Q39231"
    (qprop, qval), = p["qualifiers"]
    assert qprop == "P3831" and qval["value"]["id"] == "Q327532"
    (rprop, _), = p["references"]
    assert rprop == "P4656"
    assert not p["is_removal"]


def test_output_file_is_registered_in_atomic_files():
    assert sh.OUTPUT_FILE in dde.ATOMIC_FILES


# ─────────── redirect targets that land on the wrong entity ───────────

def test_a_redirect_to_a_weapon_class_is_refused():
    """大神神社 (栃木市): [[鉾]] redirects to 矛, the weapon CLASS. P825 would point
    at a type, not this shrine's halberd."""
    assert sh.extract_shintai("[[鉾]]") is None


def test_a_redirect_to_a_park_is_refused():
    """皆野椋神社: [[蓑山]] redirects to 美の山公園, a park (P31=Q22698)."""
    assert sh.extract_shintai("[[蓑山]]") is None


def test_refused_targets_each_record_why():
    assert sh.REFUSED_TARGETS and all(v.strip() for v in sh.REFUSED_TARGETS.values())


def test_a_harmless_redirect_is_still_accepted():
    """富士山 (代表的なトピック) is ALSO a jawiki redirect -> 富士山, but the same
    entity. A blanket 'refuse redirects' rule would have dropped Mount Fuji."""
    assert sh.extract_shintai("[[富士山 (代表的なトピック)|富士山]]（[[神体山]]）")         == "富士山 (代表的なトピック)"
