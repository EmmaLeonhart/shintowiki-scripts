"""Tests for the label-overwrite audit's parsing and classification.

The audit itself needs live Wikidata, so what is pinned here is the part that
can be wrong offline: reading a QuickStatements line and deciding what it would
do. Both halves have a way of failing silently.

A removal is written `-Qxxx|Len|"…"`. Reading the dash as part of the QID, or
ignoring it, turns a deletion into an add and the audit reports the opposite of
the truth — which for a tool whose entire job is "tell me what this would
destroy" is the worst available bug.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_label_overwrites import classify, label_lines  # noqa: E402


def test_plain_label_line_is_parsed():
    assert label_lines('Q42|Len|"Foo Shrine"\n') == [("Q42", "en", "Foo Shrine", False)]


def test_removal_line_is_flagged_not_read_as_an_add():
    assert label_lines('-Q42|Len|"Foo Shrine"\n') == [("Q42", "en", "Foo Shrine", True)]


def test_hyphenated_language_codes_are_parsed():
    """zh-hans and friends are real label languages here."""
    assert label_lines('Q42|Lzh-hans|"神社"\n')[0][1] == "zh-hans"


def test_non_label_commands_are_ignored():
    text = ('Q42|P31|Q845945\n'
            'Q43|Den|"Shinto shrine in Japan"\n'
            'Q44|Len|"Bar Shrine"\n'
            'Q45|P1814|"みしま"\n')
    assert [r[0] for r in label_lines(text)] == ["Q44"]


def test_a_description_command_is_not_mistaken_for_a_label():
    """Den and Len differ by one letter and the audit is only about labels."""
    assert label_lines('Q42|Den|"x"\n') == []


def test_blank_and_malformed_lines_do_not_crash():
    assert label_lines('\n\nnot a line\nQ1|Len|unquoted\n') == []


def test_classify_add_when_no_current_label():
    assert classify(None, "Foo", False) == "ADD"


def test_classify_noop_when_identical():
    assert classify("Foo", "Foo", False) == "NO-OP"


def test_classify_overwrite_when_different():
    assert classify("Karai Shrine", "Honoikazuchi Shrine", False) == "OVERWRITE"


def test_classify_removal_of_an_existing_label_is_a_remove():
    assert classify("Foo", "Foo", True) == "REMOVE"


def test_classify_removal_of_an_absent_label_is_a_noop():
    assert classify(None, "Foo", True) == "NO-OP"


def test_whitespace_difference_counts_as_an_overwrite():
    """Trailing space is a real difference on Wikidata and would be a real edit;
    treating it as a no-op would hide the edit from the audit."""
    assert classify("Foo Shrine ", "Foo Shrine", False) == "OVERWRITE"
