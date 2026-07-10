"""Coordinate-based resolution of a Ronsha's several addresses (Emma 2026-07-10).

The Kokugakuin record has no address field, so the rule became: read its coordinates,
reverse-geocode them, keep the address whose 都道府県 + 市区町村 matches. Resolution
requires EXACTLY one match; anything else is held for a human.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import resolve_ronsha_addresses as rr  # noqa: E402


# ─────────────────────── coordinate parsing ───────────────────────

TAKIHARA = "＋現社名など（１）緯度経度 北緯 34 度 21 分 57.77 秒 東経 136 度 25 分 33.28 秒"


def test_dms_to_decimal():
    assert rr.dms_to_decimal(34, 21, 57.77) == pytest.approx(34.366047, abs=1e-6)


def test_parses_the_real_kokugakuin_coordinate_line():
    assert rr.parse_coords(TAKIHARA) == [(34.366047, 136.425911)]


def test_a_repeated_identical_coordinate_is_one_site():
    assert len(rr.parse_coords(TAKIHARA + " " + TAKIHARA)) == 1


def test_two_different_coordinates_are_two_sites():
    second = "北緯 35 度 24 分 48.99 秒 東経 133 度 0 分 42.61 秒"
    assert len(rr.parse_coords(TAKIHARA + " " + second)) == 2


def test_a_record_with_no_coordinates_yields_none():
    assert rr.parse_coords("大分類 式内社データベース 旧郡名 度会郡") == []


RAW_HTML = ('<tr><th>+現社名など（１）緯度経度</th><td>北緯 33 度 36 分 34.56 秒 '
            '<br />東経 134 度 22 分 2.05 秒</td></tr>')


def test_raw_html_defeats_the_regex_without_tag_stripping():
    """The <br /> between 北緯 and 東経. The first live run reported '0 coordinate
    sets' for all 33 items because parse_coords was handed raw HTML."""
    assert rr.parse_coords(RAW_HTML) == []


def test_visible_text_recovers_the_coordinate():
    assert rr.parse_coords(rr.visible_text(RAW_HTML)) == [(33.6096, 134.367236)]


def test_visible_text_drops_scripts_and_styles():
    html = "<script>var 北緯 = 1;</script><style>a{}</style><p>北緯 1 度 0 分 0 秒 東経 2 度 0 分 0 秒</p>"
    assert rr.parse_coords(rr.visible_text(html)) == [(1.0, 2.0)]


# ─────────────────────── municipality normalisation ───────────────────────

def test_an_ordinance_city_ward_splits_into_two_parts():
    """GSI writes `横浜市　西区` with an ideographic space."""
    assert rr.normalise_municipality("横浜市　西区") == ["横浜市", "西区"]


def test_a_plain_town_is_one_part():
    assert rr.normalise_municipality("大紀町") == ["大紀町"]


# ─────────────────────── address matching ───────────────────────

def test_an_address_in_the_right_place_matches():
    assert rr.address_matches("三重県度会郡大紀町滝原872", "三重県", "大紀町")


def test_a_different_prefecture_does_not_match():
    assert not rr.address_matches("神奈川県伊勢原市三ノ宮1472", "三重県", "大紀町")


def test_a_different_municipality_in_the_right_prefecture_does_not_match():
    assert not rr.address_matches("三重県伊勢市宇治館町1", "三重県", "大紀町")


def test_an_ordinance_city_requires_both_city_and_ward():
    assert rr.address_matches("神奈川県横浜市西区中央1-1", "神奈川県", "横浜市　西区")
    assert not rr.address_matches("神奈川県横浜市南区中央1-1", "神奈川県", "横浜市　西区")


# ─────────────────────── resolution ───────────────────────

ADDRS = ["三重県度会郡大紀町滝原872", "神奈川県伊勢原市三ノ宮1472"]


def test_exactly_one_match_resolves():
    keep, drop = rr.resolve_address(ADDRS, "三重県", "大紀町")
    assert keep == "三重県度会郡大紀町滝原872"
    assert drop == ["神奈川県伊勢原市三ノ宮1472"]


def test_no_match_is_held():
    keep, drop = rr.resolve_address(ADDRS, "東京都", "千代田区")
    assert keep is None and drop == []


def test_two_matches_are_held():
    """Hibita Shrine: 神奈川県伊勢原市三ノ宮1472 vs …1468 — same municipality."""
    both = ["神奈川県伊勢原市三ノ宮1472", "神奈川県伊勢原市三ノ宮1468"]
    keep, drop = rr.resolve_address(both, "神奈川県", "伊勢原市")
    assert keep is None and drop == []


def test_resolution_never_invents_an_address():
    keep, drop = rr.resolve_address(ADDRS, "三重県", "大紀町")
    assert keep in ADDRS
    assert all(d in ADDRS for d in drop)


def test_the_dropped_set_excludes_the_kept_one():
    keep, drop = rr.resolve_address(ADDRS, "三重県", "大紀町")
    assert keep not in drop


# ─────────────────────── the script emits nothing ───────────────────────

def test_the_module_never_writes_quickstatements():
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "resolve_ronsha_addresses.py"),
        encoding="utf-8").read()
    assert "ATOMIC_FILES" not in src
    assert "P6375|" not in src           # no QS line construction
    assert "REPORT ONLY" in src


def test_the_muni_entry_regex_reads_the_real_gsi_format():
    line = "GSI.MUNI_ARRAY[\"24471\"] = '24,三重県,24471,大紀町';"
    code, payload = rr._MUNI_ENTRY.findall(line)[0]
    assert code == "24471"
    assert payload.split(",")[1] == "三重県"
    assert payload.split(",")[3] == "大紀町"
