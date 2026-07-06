"""Tests for generate_kana_en_labels — QuickStatements emission for Stage 1."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_kana_en_labels import lines_for_item  # noqa: E402


def test_jinja_emits_label_line_only():
    lines = lines_for_item({"qid": "Q123", "ja": "春日神社", "kana": "かすがじんじゃ"})
    assert lines == ['Q123|Len|"Kasuga Shrine"']


def test_taisha_emits_label_only():
    # Emma 2026-07-06 rule: most-common English label only, NO aliases (the
    # "Kasuga Taisha" alias is no longer emitted).
    lines = lines_for_item({"qid": "Q42", "ja": "春日大社", "kana": "かすがたいしゃ"})
    assert lines == [
        'Q42|Len|"Kasuga Grand Shrine"',
    ]


def test_pure_jingu_emits_nothing():
    # 神宮 is ambiguous -> skipped at Stage 1, falls through to the LLM
    assert lines_for_item({"qid": "Q5", "ja": "明治神宮", "kana": "めいじじんぐう"}) == []


def test_no_kana_emits_nothing():
    assert lines_for_item({"qid": "Q1", "ja": "謎神社", "kana": ""}) == []


def test_unhandled_suffix_emits_nothing():
    # ...yama is not a shrine suffix -> Stage 1 skips it (falls through)
    assert lines_for_item({"qid": "Q9", "ja": "春日山", "kana": "かすがやま"}) == []


def test_unromanizable_stem_emits_nothing():
    assert lines_for_item({"qid": "Q7", "ja": "漢字神社", "kana": "漢字じんじゃ"}) == []
