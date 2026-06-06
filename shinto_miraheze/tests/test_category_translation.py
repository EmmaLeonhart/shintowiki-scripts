"""Unit tests for the deterministic logic in generate_category_translation_moves.

The Wikidata/wiki resolvers are network; here we test the dated-maintenance
transform (the only pure deterministic piece) thoroughly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_category_translation_moves as g  # noqa: E402


def test_dated_year_month():
    assert (g.dated_transform("Articles lacking in-text citations from 2020年2月")
            == "Category:Articles lacking in-text citations from February 2020")


def test_dated_long_timestamp_collapses_to_month():
    # The day/weekday/time/(UTC) tail is dropped onto the canonical month form.
    assert (g.dated_transform("Articles lacking sources from 2016年5月31日 (火) 13:15 (UTC)")
            == "Category:Articles lacking sources from May 2016")


def test_dated_requires_english_prefix():
    # A bare JP date with no English prefix is NOT a deterministic-English case.
    assert g.dated_transform("2020年2月") is None


def test_dated_non_date_is_none():
    assert g.dated_transform("さいたま市の神社") is None
    assert g.dated_transform("WikiProject用テンプレート") is None


def test_dated_all_months():
    for n, name in g._JP_MONTHS.items():
        out = g.dated_transform(f"Foo from 2021年{n}月")
        assert out == f"Category:Foo from {name} 2021"
