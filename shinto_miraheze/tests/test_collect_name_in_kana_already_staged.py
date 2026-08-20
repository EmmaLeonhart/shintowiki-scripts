"""The collector must not stage a second P1814 line for an already-staged item.

Queue item A0 documented this hazard from the BUILDER's end on 2026-08-04: a
rebuild re-created work-files for work already done, and answering them would
have written a second identical statement each. `already_handled()` fixed that
side. The collector kept appending to the staged file unconditionally, so the
same hazard survived from the other end — and it had a live instance:

    Q11544511 (機殿神社) was hand-staged 2026-08-19; its work-file was never
    retired, so it sat in name_in_kana/ with an EMPTY answer marker. Anyone or
    anything filling that marker would have produced the duplicate.

The empty marker is why the guard runs BEFORE the answer is parsed: an
answer-first order counts these pending forever and never retires them.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collect_name_in_kana import already_staged  # noqa: E402


def _write(tmp_path, text):
    p = tmp_path / "name_in_kana.txt"
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    return str(p)


def test_reads_qids_off_the_staged_file(tmp_path):
    path = _write(tmp_path,
                  'Q11544511|P1814|"はたどのじんじゃ"|S143|Q177837|S4656|"https://x"\n'
                  'Q135186223|P1814|"かんはとりはたどのじんじゃ"\n')
    assert already_staged(path) == {"Q11544511", "Q135186223"}


def test_missing_staged_file_is_empty_not_an_error(tmp_path):
    """A first run has no staged file; that must not crash the collector."""
    assert already_staged(str(tmp_path / "nope.txt")) == set()


def test_a_qid_appearing_only_as_a_VALUE_is_not_treated_as_staged(tmp_path):
    """Same trap `strip_husk_lines.py` has tests for: a QID on the right-hand
    side is a statement ABOUT another item, not a staged line for it."""
    path = _write(tmp_path, 'Q1|P612|Q11544511\n')
    assert already_staged(path) == {"Q1"}


def test_qid_prefix_is_not_a_match(tmp_path):
    """Q1234560 must not be read as staging Q123456."""
    path = _write(tmp_path, 'Q1234560|P1814|"あ"\n')
    got = already_staged(path)
    assert got == {"Q1234560"} and "Q123456" not in got


def test_removal_line_is_not_read_as_a_staged_add(tmp_path):
    """A leading dash is the REMOVE command; the item has no add staged, so a
    later answer for it is legitimate work and must not be skipped."""
    path = _write(tmp_path, '-Q11544511|P1814|"はたどのじんじゃ"\n')
    assert already_staged(path) == set()
