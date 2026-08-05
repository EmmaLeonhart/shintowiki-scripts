"""Tests for the post-generation husk strip.

The strip is a treadmill by design: A5 says generators will keep re-emitting
husk lines on every CI regeneration, because each husk now IS the shrine item a
sitelink lookup resolves to. So this runs after generation and removes them,
keeping the staged files clean without adding a filter to twenty generators.

The risk to guard against is the opposite of the obvious one. A strip that is
too eager silently deletes real staged work, and nothing would notice — the
files are large and machine-generated. So most of what is pinned here is what
the strip must NOT touch.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from strip_husk_lines import husk_lines, strip  # noqa: E402
from direct_daily_edits import REPURPOSED  # noqa: E402

HUSK = sorted(REPURPOSED)[0]


def test_husk_subject_line_is_found_and_removed():
    text = f'{HUSK}|P825|Q123\n'
    assert len(husk_lines(text)) == 1
    assert strip(text) == ""


def test_husk_removal_line_is_found():
    """A REMOVE is written `-Qxxx|P…`; the dash is the command, not the QID.
    Missing this would leave the one line that actively edits the husk."""
    text = f'-{HUSK}|P825|Q123\n'
    assert len(husk_lines(text)) == 1


def test_normal_lines_are_untouched():
    text = 'Q42|P825|Q1\nQ43|Len|"Foo Shrine"\n-Q44|P31|Q845945\n'
    assert husk_lines(text) == []
    assert strip(text) == text


def test_only_the_subject_matters_not_the_value():
    """A husk QID appearing as a VALUE is a statement ABOUT another item — it
    does not edit the husk, so removing it would delete real work."""
    text = f'Q42|P612|{HUSK}\n'
    assert husk_lines(text) == []
    assert strip(text) == text


def test_a_qid_that_merely_starts_with_a_husk_qid_is_not_matched():
    """Q1234567 must not match husk Q123456. The delimiter is what prevents it."""
    longer = HUSK + "0"
    text = f'{longer}|P825|Q1\n'
    assert husk_lines(text) == []


def test_surrounding_lines_survive_a_strip():
    text = f'Q42|P825|Q1\n{HUSK}|P825|Q2\nQ43|P825|Q3\n'
    assert strip(text) == 'Q42|P825|Q1\nQ43|P825|Q3\n'


def test_tab_separated_subject_is_matched():
    text = f'{HUSK}\tP825\tQ123\n'
    assert len(husk_lines(text)) == 1


def test_strip_of_an_all_husk_file_does_not_emit_a_stray_newline():
    assert strip(f'{HUSK}|P825|Q1\n') == ""


def test_husk_list_is_not_empty():
    """A strip driven by an empty set is a no-op that still reports success."""
    assert REPURPOSED
