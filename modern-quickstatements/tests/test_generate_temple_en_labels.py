"""Tests for generate_temple_en_labels — QuickStatements emission for temples."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_temple_en_labels import lines_for_item  # noqa: E402


def test_ji_emits_label_line():
    lines = lines_for_item({"qid": "Q123", "ja": "金閣寺", "kana": "きんかくじ"})
    assert lines == ['Q123|Len|"Kinkaku-ji Temple"']


def test_in_emits_label_line():
    lines = lines_for_item({"qid": "Q42", "ja": "三千院", "kana": "さんぜんいん"})
    assert lines == ['Q42|Len|"Sanzen-in Temple"']


def test_no_kana_emits_nothing():
    assert lines_for_item({"qid": "Q1", "ja": "謎寺", "kana": ""}) == []


def test_non_temple_kanji_emits_nothing():
    assert lines_for_item({"qid": "Q9", "ja": "○○教会", "kana": "まるまるきょうかい"}) == []


def test_unromanizable_stem_emits_nothing():
    assert lines_for_item({"qid": "Q7", "ja": "漢寺", "kana": "漢じ"}) == []
