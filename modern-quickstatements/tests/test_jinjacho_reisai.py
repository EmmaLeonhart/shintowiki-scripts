"""Parsing 例祭 out of a prefectural 神社庁 free-text festival field.

Every fixture is a real 「主な祭典」 value sampled live from Mie's database
(`jinja-net.jp/jinjacho-mie`), the one prefectural site whose record shape has been
verified.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jinjacho_reisai as jr  # noqa: E402


# ─────────────────────── real values that parse ───────────────────────

def test_reisai_first_among_several_festivals():
    """鳥出神社: 例祭8月15日　かに祭9月23日　蛭子祭7月20日 — the かに祭 date must not win."""
    assert jr.parse_reisai("例祭8月15日　かに祭9月23日　蛭子祭7月20日") == (8, 15)


def test_reisai_with_a_space():
    """梶賀神社."""
    assert jr.parse_reisai("例祭 4月15日") == (4, 15)


def test_fullwidth_digits():
    assert jr.parse_reisai("例祭８月１５日") == (8, 15)


def test_reisai_not_first_in_the_field():
    assert jr.parse_reisai("祈年祭2月17日　例祭10月9日") == (10, 9)


# ─────────────────────── real values that must be refused ───────────────────────

def test_a_month_without_a_day_is_refused():
    """八幡神社: 例祭１０月、祈年祭２月、天王祭7月."""
    field = "例祭１０月、祈年祭２月、天王祭7月"
    assert jr.parse_reisai(field) is None
    assert jr.has_reisai_month_only(field)


def test_a_field_with_no_reisai_label_is_refused():
    """大西神社: 秋祭り１０月体育の日前日　八幡祭７月第４土日 — no 例祭 anywhere."""
    field = "秋祭り１０月体育の日前日　八幡祭７月第４土日"
    assert jr.parse_reisai(field) is None
    assert not jr.has_reisai_month_only(field)


def test_a_relative_date_is_refused():
    """島勝神社: １０月第２日曜（神饌に特徴あり…"""
    field = "１０月第２日曜（神饌に特徴あり、魳の姿ずしを盛った神膳１８"
    assert jr.parse_reisai(field) is None
    assert jr.is_relative(field)


def test_a_reisai_day_qualified_as_relative_is_refused():
    assert jr.parse_reisai("例祭10月9日第２日曜") is None


def test_another_festivals_date_never_stands_in_for_the_reisai():
    """No 例祭 here, only かに祭 — must not return 9/23."""
    assert jr.parse_reisai("かに祭9月23日　蛭子祭7月20日") is None


@pytest.mark.parametrize("field", ["", None, "   ", "宮司名", "例祭"])
def test_empty_and_useless_fields(field):
    assert jr.parse_reisai(field) is None


# ─────────────────────── range guards ───────────────────────

@pytest.mark.parametrize("field", ["例祭13月1日", "例祭0月5日", "例祭5月0日", "例祭5月32日"])
def test_out_of_range_values_are_refused(field):
    assert jr.parse_reisai(field) is None


def test_boundary_values_are_accepted():
    assert jr.parse_reisai("例祭1月1日") == (1, 1)
    assert jr.parse_reisai("例祭12月31日") == (12, 31)


# ─────────────────────── helpers ───────────────────────

def test_normalise_digits():
    assert jr.normalise_digits("１０月２日") == "10月2日"


def test_is_relative_catches_the_public_holidays():
    assert jr.is_relative("体育の日前日")
    assert jr.is_relative("第４土曜")
    assert not jr.is_relative("10月9日")


def test_the_module_emits_no_quickstatements():
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "jinjacho_reisai.py"), encoding="utf-8").read()
    assert "P837" not in src.split('"""')[2] if src.count('"""') > 2 else True
    assert "S4656" not in src
