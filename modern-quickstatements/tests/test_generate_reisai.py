"""Tests for generate_reisai_quickstatements parse + QS-line (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_reisai_quickstatements import parse_reisai_date, qs_line  # noqa: E402


def _ib(reisai):
    return "{{神社\n| 名称 = X\n| 例祭 = " + reisai + "\n| 主祭神 = Y\n}}"


def test_fixed_date_with_festival_name():
    assert parse_reisai_date(_ib("[[4月15日]]（御頭祭、酉の祭）")) == (4, 15)


def test_plain_fixed_date():
    assert parse_reisai_date(_ib("[[5月3日]]")) == (5, 3)
    assert parse_reisai_date(_ib("10月17日")) == (10, 17)


def test_lunar_skipped():
    assert parse_reisai_date(_ib("旧暦6月15日")) is None


def test_relative_date_skipped():
    assert parse_reisai_date(_ib("4月第2日曜日")) is None


def test_no_field_returns_none():
    assert parse_reisai_date("{{神社\n| 名称 = X\n}}") is None


def test_qs_line_shape():
    line = qs_line("Q999", "Q2519", "諏訪大社")
    # reference is the jawiki import URL only (S4656) — no separate stated-in
    assert line.startswith("Q999|P837|Q2519|P3831|Q11385469|S4656|\"https://ja.wikipedia.org/wiki/")
    assert "S248" not in line


def test_qs_line_parses_in_pipeline():
    # the emitted line must round-trip through the direct_daily_edits parser
    import direct_daily_edits as dde
    p = dde.parse_qs_line(qs_line("Q999", "Q2519", "諏訪大社"))
    assert p["property"] == "P837"
    assert p["value"]["value"]["id"] == "Q2519"
    assert p["qualifiers"][0][0] == "P3831"          # object-has-role = Reisai
    assert p["qualifiers"][0][1]["value"]["id"] == "Q11385469"
    assert p["references"]                            # jawiki citation present
