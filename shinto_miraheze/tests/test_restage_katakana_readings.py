"""Tests for recovering the mixed-script readings the old gate discarded.

The parsing risk here is specific and would be silent: the log's third column is
the answer as written, and most of these rows carry an explanatory note after an
em-dash ("ハワイだいじんぐう — mixed script; ハワイ is a katakana place name").
Staging that whole string as a reading would write the commentary into P1814.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restage_katakana_readings import already_staged, katakana_entries  # noqa: E402


def test_reading_is_cut_at_the_em_dash_note():
    log = ("Q1\tKATAKANA\tハワイだいじんぐう — mixed script; ハワイ is a place name\n")
    assert katakana_entries(log) == [("Q1", "ハワイだいじんぐう")]


def test_reading_without_a_note_is_taken_whole():
    assert katakana_entries("Q1\tKATAKANA\tペリリューじんじゃ\n") == [
        ("Q1", "ペリリューじんじゃ")]


def test_other_statuses_are_ignored():
    """KANA rows are already staged; NO_KANA and NOT_A_SHRINE produced nothing
    on purpose. Restaging any of them would double-write or resurrect a refusal."""
    log = ("Q1\tKANA\tみしまたいしゃ\n"
           "Q2\tNO_KANA\tthe lead gives no reading\n"
           "Q3\tNOT_A_SHRINE\tQ5 (human)\n"
           "Q4\tKATAKANA\tサムハラじんじゃ\n")
    assert katakana_entries(log) == [("Q4", "サムハラじんじゃ")]


def test_malformed_rows_do_not_crash():
    assert katakana_entries("garbage\n\nQ1\tKATAKANA\n") == []


def test_punctuation_is_cleaned_from_the_reading():
    assert katakana_entries("Q1\tKATAKANA\tスワトウ・じんじゃ\n") == [
        ("Q1", "スワトウじんじゃ")]


def test_already_staged_reads_subjects(tmp_path):
    p = tmp_path / "name_in_kana.txt"
    p.write_text('Q1|P1814|"みしま"\nQ2|P1814|"おおやま"\n', encoding="utf-8")
    assert already_staged(str(p)) == {"Q1", "Q2"}


def test_already_staged_of_a_missing_file_is_empty():
    assert already_staged("/nonexistent/name_in_kana.txt") == set()
