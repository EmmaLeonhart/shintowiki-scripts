"""Tests for the 伝-date (presumed founding date) importer.

The load-bearing invariant: this script and its sibling
`generate_souken_quickstatements` have DISJOINT accept-sets. A field is either a
clean recorded year or a traditional one, never both, so no date is ever imported
twice — once as fact and once as presumption.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_souken_quickstatements as souken  # noqa: E402
import generate_souken_den_quickstatements as den  # noqa: E402


TRADITIONAL = [
    ("伝[[大同 (日本)|大同]]2年（[[807年]]）", 807),
    ("（伝）[[天平]]元年（[[729年]]）", 729),
    ("社伝によれば[[貞観 (日本)|貞観]]5年（[[863年]]）", 863),
    ("寺伝では[[延暦]]13年（[[794年]]）", 794),
    ("伝承では[[1185年]]", 1185),
]

NOT_TRADITIONAL = [
    "[[貞観 (日本)|貞観]]5年（[[863年]]）",   # clean — the sibling's job
    "不詳",
    "伝 不詳",                                 # traditional AND unknown
    "伝[[807年]]頃",                           # traditional AND circa
    "伝[[8世紀]]",                             # traditional AND century-only
    "伝[[天平]]年間",                          # traditional AND era-span
    "伝[[807年]]以前",                         # traditional AND "before"
    "伝[[807年]]、[[810年]]",                  # two distinct years
    "伝[[大同 (日本)|大同]]2年",               # traditional, no Gregorian year
    "",
]


@pytest.mark.parametrize("field,year", TRADITIONAL)
def test_traditional_dates_yield_their_year(field, year):
    assert den.parse_den_year(field) == year


@pytest.mark.parametrize("field", NOT_TRADITIONAL)
def test_non_traditional_or_vague_fields_are_refused(field):
    assert den.parse_den_year(field) is None


@pytest.mark.parametrize("field,_year", TRADITIONAL)
def test_sibling_refuses_everything_this_script_accepts(field, _year):
    """generate_souken_quickstatements skips on 伝 — so the sets cannot overlap."""
    assert souken.parse_year(field) is None


@pytest.mark.parametrize("field", [f for f, _ in TRADITIONAL] + NOT_TRADITIONAL)
def test_accept_sets_are_disjoint(field):
    accepted_here = den.parse_den_year(field) is not None
    accepted_there = souken.parse_year(field) is not None
    assert not (accepted_here and accepted_there), field


def test_clean_year_is_accepted_by_the_sibling_only():
    field = "[[貞観 (日本)|貞観]]5年（[[863年]]）"
    assert souken.parse_year(field) == 863
    assert den.parse_den_year(field) is None


def test_era_year_noise_below_300_is_not_mistaken_for_a_year():
    """'2年' in 大同2年 must not be read as the year 2."""
    assert den.parse_den_year("伝[[大同 (日本)|大同]]2年（[[807年]]）") == 807


def test_html_comments_and_sfn_are_stripped_before_parsing():
    assert den.parse_den_year("伝[[807年]]<!-- [[900年]] -->") == 807
    assert den.parse_den_year("伝[[807年]]{{sfn|Foo|2001|p=9}}") == 807


# ------------------------------------------------------------ line shape

def test_qs_line_carries_the_presumably_qualifier_and_the_source():
    line = den.qs_line("Q42", 807, "https://ja.wikipedia.org/wiki/X")
    assert line == (
        'Q42|P571|+0807-00-00T00:00:00Z/9|P1480|Q18122778|'
        'S4656|"https://ja.wikipedia.org/wiki/X"')


def test_year_is_zero_padded_to_four_digits():
    assert "+0729-" in den.qs_line("Q1", 729, "u")


def test_precision_is_year_not_day():
    assert den.qs_line("Q1", 807, "u").split("|")[2].endswith("/9")


def test_qualifier_entities_are_the_verified_ones():
    assert den.P_SOURCING == "P1480"
    assert den.PRESUMABLY == "Q18122778"


def test_no_line_is_a_removal():
    assert not den.qs_line("Q1", 807, "u").startswith("-")


# ------------------------------------------------------------ the two live bugs
# Both fields below are the real jawiki text, and both produced a confident, wrong
# P571 on the first full run (639 lines) before these guards existed.

TAKERINJI = "伝・[[奈良時代]]初期<br />再興：[[平成]]9年（[[1997年]]）"
OMIKE = (
    "不明<ref name=\"#1\">『上伊那郡史』唐沢貞治郎　1921年　上伊那郡教育会</ref>"
    "{{Sfn |唐沢貞治郎 |1921 |p=969 }}"
)


def test_restoration_year_is_not_the_founding_year():
    """竹林寺 (生駒市): the traditional founding is 'early Nara period' — no Gregorian
    year at all. 1997 belongs to the 再興. It imported 1997 as inception."""
    assert den.parse_den_year(TAKERINJI) is None


def test_a_year_in_the_den_segment_still_survives_a_sibling_rebuild_segment():
    field = "伝・[[寛弘]]元年（[[1004年]]）<br />再興：[[平成]]9年（[[1997年]]）"
    assert den.parse_den_year(field) == 1004


def test_unknown_founding_with_a_citation_year_is_refused():
    """大御食神社: the field is literally 不明; 1921 is a citation's publication year."""
    assert den.parse_den_year(OMIKE) is None
    assert souken.parse_year(OMIKE) is None


def test_fumei_is_vague_not_just_fushou():
    assert den.parse_den_year("伝 不明") is None
    assert souken.parse_year("不明（[[1921年]]）") is None


def test_reference_publication_years_never_leak():
    field = '伝[[807年]]<ref name="a">『郡史』1921年</ref>'
    assert den.parse_den_year(field) == 807


def test_nested_refnest_template_is_stripped_whole():
    """A regex stopping at the first }} left the outer template's years behind."""
    field = "伝[[807年]]{{Refnest|group=注|『書』{{NDLDC|123}} 1921年}}"
    assert den.parse_den_year(field) == 807


def test_self_closing_ref_is_stripped():
    assert den.parse_den_year('伝[[807年]]<ref name="a" />') == 807


def test_sibling_refuses_rebuild_markers_since_it_cannot_scope_them():
    """souken has no 伝 anchor to scope by, so it declines rather than guess."""
    assert souken.parse_year("[[奈良時代]]初期<br />再興：[[平成]]9年（[[1997年]]）") is None
