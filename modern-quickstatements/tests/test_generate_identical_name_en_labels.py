"""Tests for generate_identical_name_en_labels — Stage 2 normalize + emission."""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_identical_name_en_labels import normalize_en, lines_for_target  # noqa: E402


def test_normalize_strips_paren_disambiguator():
    # reusing "(Oita)" verbatim on a different shrine would be wrong
    assert normalize_en("Maruyama Shrine (Oita)") == "Maruyama Shrine"


def test_normalize_plain_label_unchanged():
    assert normalize_en("Mishima Shrine") == "Mishima Shrine"


def test_lines_dominant_label_only():
    counters = {"三島神社": Counter({"Mishima Shrine": 9})}
    assert lines_for_target("Q1", "三島神社", counters) == ['Q1|Len|"Mishima Shrine"']


def test_lines_two_readings_emit_label_and_alias():
    counters = {"諏訪神社": Counter({"Suwa Shrine": 3, "Suwa Jinja": 1})}
    assert lines_for_target("Q1", "諏訪神社", counters) == [
        'Q1|Len|"Suwa Shrine"',
        'Q1|Aen|"Suwa Jinja"',
    ]


def test_lines_no_match_emits_nothing():
    assert lines_for_target("Q1", "無名神社", {}) == []


def test_lines_empty_counter_emits_nothing():
    assert lines_for_target("Q1", "無名神社", {"無名神社": Counter()}) == []
