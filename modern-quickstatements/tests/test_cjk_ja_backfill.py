"""Tests for cjk_ja_backfill (C1): a shrine with no ja label but a CJK-ideographic
name (zh family) gets that name copied onto its ja label. Guarded so only genuine
CJK ideographs are copied — never hangul or Latin."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_cjk_ja_backfill import is_cjk_ideographic, lines_for  # noqa: E402


def test_kanji_label_is_cjk():
    assert is_cjk_ideographic("西山神社")
    assert is_cjk_ideographic("大溪社")


def test_latin_label_not_cjk():
    assert not is_cjk_ideographic("Nishiyama Shrine")


def test_hangul_label_not_cjk():
    assert not is_cjk_ideographic("서울 신사")


def test_mixed_label_not_cjk():
    # a romanized disambiguator mixed in -> reject (not a clean ja label)
    assert not is_cjk_ideographic("西山神社 (Taiwan)")


def test_lines_for_kanji_emits_lja():
    assert lines_for("Q138684951", "西山神社") == ['Q138684951|Lja|"西山神社"']


def test_lines_for_non_cjk_emits_nothing():
    assert lines_for("Q1", "Nishiyama Shrine") == []


def test_lines_for_quote_in_label_skipped():
    assert lines_for("Q1", '西"山') == []
