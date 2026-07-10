"""被葬者 (interred person) import — P119 + P547, P1480 on the hedged ones.

Every fixture is real text from a live jawiki kofun infobox. The traps are all real:
the wikilink is often the ATTRIBUTOR (宮内庁), the hedge sits outside the link, rival
candidates are separated by <br>, and several link targets are not people at all.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_hisousha_quickstatements as hs  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


# ─────────────────────── the attributor trap ───────────────────────

def test_the_imperial_household_agency_is_never_the_occupant():
    """大仙陵古墳: （[[宮内庁]]治定）第16代[[仁徳天皇]]. 宮内庁 says so; 仁徳天皇 is buried."""
    person, uncertain = hs.extract_person("（[[宮内庁]]治定）第16代[[仁徳天皇]]")
    assert person == "仁徳天皇"
    assert uncertain is True


def test_every_attributor_is_excluded():
    for name in hs.ATTRIBUTORS:
        person, _ = hs.extract_person("（[[{}]]治定）[[明治天皇]]".format(name))
        assert person == "明治天皇"


def test_an_attributor_alone_yields_nobody():
    assert hs.extract_person("（[[宮内庁]]治定）")[0] is None


# ─────────────────────── hedges ───────────────────────

@pytest.mark.parametrize("field,person", [
    ("（推定）第26代[[継体天皇]]", "継体天皇"),                    # 今城塚古墳
    ("（[[宮内庁]]推定）第21代[[雄略天皇]]", "雄略天皇"),
    ("（推定）[[蘇我馬子]]", "蘇我馬子"),                         # 石舞台古墳
    ("（推定）[[筑紫君磐井]]", "筑紫君磐井"),                      # 岩戸山古墳
])
def test_hedged_values_yield_the_person_and_are_marked(field, person):
    got, uncertain = hs.extract_person(field)
    assert got == person
    assert uncertain is True


@pytest.mark.parametrize("field,person", [
    ("[[明治天皇]]", "明治天皇"),        # 伏見桃山陵
    ("[[大正天皇]]", "大正天皇"),        # 武蔵陵墓地
    ("[[楠木正行]]", "楠木正行"),        # 小楠公御墓所
    ("[[早良親王]]", "早良親王"),        # 八島陵
])
def test_the_four_unhedged_values_are_not_marked(field, person):
    got, uncertain = hs.extract_person(field)
    assert got == person
    assert uncertain is False


def test_chitei_counts_as_a_hedge():
    """治定 is an Imperial Household Agency designation, not an excavation result."""
    _p, uncertain = hs.extract_person("（宮内庁治定）[[仁徳天皇]]")
    assert uncertain is True


# ─────────────────────── refusals ───────────────────────

def test_rival_candidates_are_refused():
    """河内大塚山古墳 names 雄略天皇 OR 安閑天皇."""
    field = "（[[宮内庁]]推定）第21代[[雄略天皇]]<br />（一説）第27代[[安閑天皇]]"
    assert hs.extract_person(field)[0] is None


def test_a_person_only_inside_the_hedge_is_refused():
    """将門塚: 不明（伝・[[平将門]]） — the field says the occupant is unknown."""
    assert hs.extract_person("不明（伝・[[平将門]]）")[0] is None


@pytest.mark.parametrize("field", [
    "不明",
    "須恵器生産集団の統率者か?",
    "",
    None,
    "   ",
])
def test_unusable_values_are_refused(field):
    assert hs.extract_person(field)[0] is None


def test_the_same_person_linked_twice_is_still_one_person():
    person, _ = hs.extract_person("[[明治天皇]]（[[明治天皇]]）")
    assert person == "明治天皇"


# ─────────────────────── line shape ───────────────────────

URL = "https://ja.wikipedia.org/wiki/X"


def test_both_directions_are_emitted():
    lines = hs.qs_lines("Q1", "Q2", False, URL)
    assert lines[0] == 'Q1|P119|Q2|S4656|"%s"' % URL
    assert lines[1] == 'Q2|P547|Q1|S4656|"%s"' % URL


def test_the_hedge_rides_on_both_statements():
    lines = hs.qs_lines("Q1", "Q2", True, URL)
    assert all("|P1480|Q18122778|" in l for l in lines)


def test_an_unhedged_pair_carries_no_qualifier():
    assert not any("P1480" in l for l in hs.qs_lines("Q1", "Q2", False, URL))


def test_the_presumably_qid_is_the_one_the_den_dates_use():
    import generate_souken_den_quickstatements as den
    assert hs.PRESUMABLY == den.PRESUMABLY == "Q18122778"
    assert hs.P_SOURCING == den.P_SOURCING == "P1480"


def test_no_line_is_a_removal():
    assert all(not l.startswith("-") for l in hs.qs_lines("Q1", "Q2", True, URL))


def test_properties_are_the_verified_ones():
    assert hs.P_BURIAL == "P119"          # place of burial (person -> place)
    assert hs.P_COMMEMORATES == "P547"    # commemorates    (place -> person)


# ─────────────────────── the daily editor can execute it ───────────────────────

def test_the_daily_editor_parses_a_hedged_line():
    line = hs.qs_lines("Q42", "Q99", True, URL)[0]
    p = dde.parse_qs_line(line)
    assert p["entity"] == "Q42" and p["property"] == "P119"
    assert p["value"]["value"]["id"] == "Q99"
    (qprop, qval), = p["qualifiers"]
    assert qprop == "P1480" and qval["value"]["id"] == "Q18122778"
    (rprop, _), = p["references"]
    assert rprop == "P4656"
    assert not p["is_removal"]


def test_the_daily_editor_parses_the_reverse_direction():
    line = hs.qs_lines("Q42", "Q99", False, URL)[1]
    p = dde.parse_qs_line(line)
    assert p["entity"] == "Q99" and p["property"] == "P547"
    assert p["value"]["value"]["id"] == "Q42"
    assert p["qualifiers"] == []


def test_output_file_is_registered_in_atomic_files():
    assert hs.OUTPUT_FILE in dde.ATOMIC_FILES
