"""Tests for the province-exclusion generator and its geometry.

The load-bearing facts pinned here:
  * the criterion split (only Beppyō-alone means "did not exist");
  * every role is emitted, with no precedence order;
  * no code path can ever produce a removal line;
  * point-in-polygon respects holes and does not leak across bounding boxes;
  * the 1869 Mutsu/Dewa splits merge back to the classical provinces.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import province_geometry as pg  # noqa: E402
import generate_province_exclusions as gpe  # noqa: E402


# ------------------------------------------------------------ criterion

def test_beppyo_alone_did_not_exist():
    assert gpe.criterion_for({gpe.BEPPYO}) == gpe.NON_EXISTENCE


@pytest.mark.parametrize("classes", [
    {gpe.SHIKIGESHA},
    {gpe.KOKUSHI},
    {gpe.BEPPYO, gpe.SHIKIGESHA},
    {gpe.BEPPYO, gpe.KOKUSHI},
    {gpe.BEPPYO, gpe.KOKUSHI, gpe.SHIKIGESHA},
])
def test_shrines_that_existed_get_omission(classes):
    """Wikidata defines shikigesha and kokushi genzaisha as extant in 927, so
    'non-existence' would be a false statement about them."""
    assert gpe.criterion_for(classes) == gpe.OMISSION


# ------------------------------------------------------------ line shape

def test_single_role_line_carries_criterion():
    lines = gpe.qs_lines("Q1", "Q2", {gpe.BEPPYO})
    assert lines == ["Q1|P3113|Q2|P3831|Q10898274|P1013|Q3877969"]


def test_every_role_is_emitted_no_precedence():
    lines = gpe.qs_lines("Q1", "Q2", {gpe.BEPPYO, gpe.SHIKIGESHA})
    assert len(lines) == 2
    roles = {l.split("|")[4] for l in lines}
    assert roles == {gpe.BEPPYO, gpe.SHIKIGESHA}
    # criterion appears exactly once, on the first line
    assert sum("P1013" in l for l in lines) == 1
    assert lines[0].endswith("P1013|" + gpe.OMISSION)


def test_all_lines_target_the_same_statement():
    lines = gpe.qs_lines("Q11467693", "Q42", {gpe.BEPPYO, gpe.KOKUSHI})
    for line in lines:
        assert line.startswith("Q11467693|P3113|Q42|")


def test_no_classes_emits_nothing():
    assert gpe.qs_lines("Q1", "Q2", set()) == []


# ------------------------------------------------------------ add-only

def test_assert_add_only_passes_on_generated_lines():
    gpe.assert_add_only(gpe.qs_lines("Q1", "Q2", {gpe.BEPPYO, gpe.SHIKIGESHA}))


def test_assert_add_only_rejects_a_removal():
    with pytest.raises(RuntimeError, match="ADD-ONLY"):
        gpe.assert_add_only(["Q1|P3113|Q2", "-Q1|P3113|Q3"])


def test_generated_lines_never_start_with_dash():
    for classes in ({gpe.BEPPYO}, {gpe.KOKUSHI}, {gpe.BEPPYO, gpe.SHIKIGESHA}):
        for line in gpe.qs_lines("Q1", "Q2", classes):
            assert not line.startswith("-")


# ------------------------------------------------------------ coordinates

def test_parse_point():
    assert gpe.parse_point("Point(135.7 35.0)") == (135.7, 35.0)


def test_parse_point_rejects_junk():
    assert gpe.parse_point("somewhere") == (None, None)
    assert gpe.parse_point("Point(bad)") == (None, None)


# ------------------------------------------------------------ geometry

SQUARE = [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
HOLED = [
    [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
    [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
]


def test_point_inside_square():
    assert pg.point_in_polygon(5, 5, SQUARE)


def test_point_outside_square():
    assert not pg.point_in_polygon(15, 5, SQUARE)


def test_point_in_hole_is_outside():
    assert pg.point_in_polygon(5, 5, SQUARE)
    assert not pg.point_in_polygon(5, 5, HOLED)


def test_point_in_holed_polygon_but_not_the_hole():
    assert pg.point_in_polygon(1, 1, HOLED)


def test_locate_uses_bbox_but_still_tests_the_polygon():
    """A point inside province A's bounding box but outside its polygon must not
    be attributed to A."""
    triangle = [[[0, 0], [10, 0], [0, 10], [0, 0]]]
    index = {"A": [triangle]}
    assert pg.locate(1, 1, index) == ["A"]       # inside the triangle
    assert pg.locate(9, 9, index) == []          # inside the bbox, outside the hypotenuse


def test_locate_returns_all_hits_never_guesses():
    index = {"A": [SQUARE], "B": [SQUARE]}
    assert pg.locate(5, 5, index) == ["A", "B"]


# ------------------------------------------------------------ era mismatch

def test_mutsu_merges_the_five_meiji_provinces():
    assert set(pg.MERGES["陸奥"]) == {"磐城", "岩代", "陸前", "陸中", "陸奥"}


def test_dewa_merges_uzen_and_ugo():
    assert set(pg.MERGES["出羽"]) == {"羽前", "羽後"}


def test_hokkaido_and_ryukyu_are_dropped():
    assert "琉球" in pg.DROPPED
    assert "石狩" in pg.DROPPED
    assert len(pg.DROPPED) == 12


def test_classical_province_arithmetic():
    """73 mainland features - 7 merged-away + 2 merged targets = 68."""
    mainland = pg.N_FEATURES - len(pg.DROPPED)          # 85 - 12 = 73
    merged_away = sum(len(v) for v in pg.MERGES.values())  # 7
    assert mainland - merged_away + len(pg.MERGES) == 68


def test_tsushima_alias_uses_the_old_kanji():
    assert pg.wikidata_name_to_dataset("対馬国") == "對馬"


def test_wikidata_name_strips_kuni_suffix():
    assert pg.wikidata_name_to_dataset("山城国") == "山城"
    assert pg.wikidata_name_to_dataset("陸奥国") == "陸奥"


# ------------------------------------------------------------ island exceptions

def test_island_exceptions_are_named_not_thresholded():
    """A distance rule would fire on unseen data; these two are enumerated."""
    assert gpe.ISLAND_EXCEPTIONS == {"Q2857985": "日向", "Q11677857": "陸奥"}


def test_island_provinces_exist_after_the_merge():
    """陸奥 only exists because MERGES rebuilt it from the five 1869 provinces."""
    for province in gpe.ISLAND_EXCEPTIONS.values():
        assert province in pg.MERGES or province not in pg.DROPPED


# ------------------------------------------------------------ nearest

def test_nearest_reports_distance_and_never_assigns():
    index = {"A": [SQUARE]}
    name, km = pg.nearest(20, 5, index)
    assert name == "A"
    assert km > 0
    # locate() is the only thing that assigns, and it still says "outside"
    assert pg.locate(20, 5, index) == []
