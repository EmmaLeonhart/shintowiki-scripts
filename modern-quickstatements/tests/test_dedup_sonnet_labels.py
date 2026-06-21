"""Tests for dedup_sonnet_labels — A5: a QID handled by a higher-priority
deterministic stage (0/1/2) must not also carry a stale LLM label in
en_labels_sonnet.txt (priority inversion + double-emission)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dedup_sonnet_labels import prune_superseded  # noqa: E402


def test_removes_lines_whose_qid_is_superseded():
    sonnet = ['Q1|Len|"a"', 'Q2|Len|"b"', 'Q2|Aen|"b2"', 'Q3|Len|"c"']
    kept = prune_superseded(sonnet, superseded={"Q2"})
    assert kept == ['Q1|Len|"a"', 'Q3|Len|"c"']


def test_no_superseded_keeps_all():
    sonnet = ['Q1|Len|"a"', 'Q2|Len|"b"']
    assert prune_superseded(sonnet, superseded=set()) == sonnet


def test_blank_lines_dropped():
    sonnet = ['Q1|Len|"a"', '', '  ', 'Q2|Len|"b"']
    assert prune_superseded(sonnet, superseded=set()) == ['Q1|Len|"a"', 'Q2|Len|"b"']


def test_all_superseded_returns_empty():
    sonnet = ['Q1|Len|"a"', 'Q1|Aen|"a2"']
    assert prune_superseded(sonnet, superseded={"Q1"}) == []
