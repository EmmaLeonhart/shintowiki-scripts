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


# ─── phase 4: place-name gazetteer ──────────────────────────
def test_parse_place_history():
    assert g.parse_place_pattern("三条市の歴史") == ("三条市", "History of {}")


def test_parse_place_buildings():
    assert (g.parse_place_pattern("三宅村の建築物")
            == ("三宅村", "Buildings and structures in {}"))


def test_parse_place_shrines():
    # <place>の神社 → "Shinto shrines in <place>" (the productive shrine pattern).
    assert (g.parse_place_pattern("さいたま市の神社")
            == ("さいたま市", "Shinto shrines in {}"))


def test_parse_place_temples():
    assert (g.parse_place_pattern("京都市の寺院")
            == ("京都市", "Buddhist temples in {}"))


def test_parse_place_specific_shrine_not_matched():
    # A specific shrine named "<name>神社" has NO の before 神社, so it must NOT be
    # read as "shrines in <name>". This is the whole reason the の is in the suffix.
    assert g.parse_place_pattern("氷川神社") is None
    assert g.parse_place_pattern("三吉神社") is None


def test_shrines_category_gated_and_formatted():
    assert (g.place_category("Shinto shrines in {}", "Saitama (city)", ["Q494721"])
            == "Category:Shinto shrines in Saitama (city)")
    assert (g.place_category("Buddhist temples in {}", "Kyoto", ["Q494721"])
            == "Category:Buddhist temples in Kyoto")


def test_parse_place_important_cultural_properties():
    # <place>の重要文化財 → "Important Cultural Properties of <place>" (enwiki uses
    # "of", not "in" — verified against Category:Important Cultural Properties of
    # Kyoto Prefecture / of Hyōgo Prefecture).
    assert (g.parse_place_pattern("京都府の重要文化財")
            == ("京都府", "Important Cultural Properties of {}"))


def test_icp_category_formatted():
    assert (g.place_category("Important Cultural Properties of {}", "Kyoto Prefecture",
                             ["Q50337"])
            == "Category:Important Cultural Properties of Kyoto Prefecture")


def test_parse_place_empty_stem_is_none():
    # A bare suffix with no place stem must not match.
    assert g.parse_place_pattern("の歴史") is None


def test_parse_place_non_pattern_is_none():
    assert g.parse_place_pattern("下県郡") is None            # bare district, no suffix
    assert g.parse_place_pattern("三吉神社") is None           # a shrine, not <place>の…
    assert g.parse_place_pattern("三省堂の国語辞典") is None    # unhandled suffix


def test_place_category_gated_and_formatted():
    # Confirmed Japanese place (city of Japan) with an enwiki article → resolved.
    assert (g.place_category("History of {}", "Sanjō, Niigata", ["Q494721"])
            == "Category:History of Sanjō, Niigata")
    assert (g.place_category("Buildings and structures in {}", "Miyake, Tokyo",
                             ["Q1059478"])
            == "Category:Buildings and structures in Miyake, Tokyo")


def test_place_category_rejects_non_place_p31():
    # Stem resolves to a jawiki article that is NOT a Japanese place (e.g. a
    # religion / company class) → rejected, goes to residual.
    assert g.place_category("History of {}", "Christianity", ["Q9174"]) is None


def test_place_category_rejects_missing_enwiki():
    assert g.place_category("History of {}", "", ["Q494721"]) is None


def test_place_category_rejects_category_titled_enwiki():
    # An enwiki sitelink that is itself a Category: is not an article place name.
    assert g.place_category("History of {}", "Category:Foo", ["Q494721"]) is None
