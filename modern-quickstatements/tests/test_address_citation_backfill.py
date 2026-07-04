"""Tests for generate_address_citation_backfill: rows with real addresses are
collected (with rowspan name carry), and reference-backfill lines are emitted
only when the item's ja label matches a name cell of a row carrying exactly
that address. Also covers the shared label matcher extracted from the doujou
resolver."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_address_citation_backfill import (  # noqa: E402
    JAWIKI_ITEM, build_lines, collect_address_rows,
)
from resolve_doujou_addresses import label_matches_names  # noqa: E402

SAMPLE_TABLE = """{| class="wikitable"
|-
! 社名 !! 所在地
|-
| [[熊野大社]] || 島根県松江市八雲町熊野2451
|-
| 布吾弥神社 || 同上
|-
| 揖夜神社 || 島根県八束郡東出雲町揖屋2229
|-
| colspan=1 | 島根県松江市宍道町上来待551
|}"""


def fake_fetch(title):
    return SAMPLE_TABLE


def test_collect_rows_only_real_addresses():
    rows = collect_address_rows(["Template:T1"], fetch=fake_fetch)
    addrs = [r["address"] for r in rows]
    assert "同上" not in addrs
    assert "島根県松江市八雲町熊野2451" in addrs
    assert "島根県八束郡東出雲町揖屋2229" in addrs


def test_collect_rows_rowspan_carries_names():
    rows = collect_address_rows(["Template:T1"], fetch=fake_fetch)
    # the last row has an address but no name cell -> inherits 揖夜神社
    carry = [r for r in rows if r["address"] == "島根県松江市宍道町上来待551"]
    assert carry and carry[0]["names"] == ["揖夜神社"]


def test_label_matcher_exact_and_gōshi_prefix():
    assert label_matches_names("熊野大社", ["熊野大社"])
    assert label_matches_names("合祀：布吾弥神社", ["布吾弥神社"])


def test_label_matcher_kanji_variant_and_suffix():
    assert label_matches_names("剣神社", ["劔神社"])
    assert label_matches_names("波夜都武自和気神社", ["坐波夜都武自和気神社"])


def test_label_matcher_short_label_no_cross_match():
    assert not label_matches_names("剣神社", ["佐久多神社"])


def test_build_lines_emits_only_on_label_match():
    addr_rows = {
        "島根県松江市八雲町熊野2451": [
            {"names": ["熊野大社"], "address": "島根県松江市八雲町熊野2451",
             "template": "Template:T1"}],
    }
    url = "https://ja.wikipedia.org/wiki/X"
    bindings = [
        ("Q1", "熊野大社", "島根県松江市八雲町熊野2451"),      # match -> line
        ("Q2", "無関係神社", "島根県松江市八雲町熊野2451"),    # no match -> skip
        ("Q3", "熊野大社", "島根県どこか他所1"),               # addr not in rows -> skip
    ]
    lines, skipped = build_lines(bindings, addr_rows, url)
    assert lines == [
        f'Q1|P6375|ja:"島根県松江市八雲町熊野2451"|S143|{JAWIKI_ITEM}|S4656|"{url}"']
    assert {s[0] for s in skipped} == {"Q2", "Q3"}


def test_build_lines_dedupes_duplicate_bindings():
    addr_rows = {
        "島根県A1": [{"names": ["甲神社"], "address": "島根県A1",
                      "template": "Template:T1"}],
    }
    bindings = [("Q1", "甲神社", "島根県A1"), ("Q1", "甲神社", "島根県A1")]
    lines, skipped = build_lines(bindings, addr_rows, "u")
    assert len(lines) == 1 and not skipped
