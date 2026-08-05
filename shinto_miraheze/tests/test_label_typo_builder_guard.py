"""The label-typo builder must not re-queue work that is already finished.

Third builder bitten by the same rule, so it is worth stating plainly: "skip if
the work-file exists" is wrong because the collector DELETES the work-file when
it answers. Absence means "done" at least as often as "never queued".

The second half matters just as much here. A decision of "nothing is wrong with
this item" correctly produces NO QuickStatement, so the staged .txt cannot be
the only record consulted — those items exist solely in _resolved.log. That is
exactly the disposition all 15 remaining items got on 2026-08-05: their English
label is the conventional name and their P1814 is the registered reading, 10 of
them sourced to the National Tax Agency's 宗教法人 register. Nothing to fix, and
nothing to stage — so a staged-file-only guard would resurrect all 15.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_label_typo_review_queue as b  # noqa: E402


@pytest.fixture
def paths(tmp_path, monkeypatch):
    log = tmp_path / "_resolved.log"
    qs = tmp_path / "label_typo_fixes.txt"
    monkeypatch.setattr(b, "RESOLVED_LOG", str(log))
    monkeypatch.setattr(b, "QS_OUT", str(qs))
    return log, qs


def test_nothing_handled_when_neither_file_exists(paths):
    assert b.already_handled() == set()


def test_resolved_log_entries_are_handled(paths):
    log, _ = paths
    log.write_text("Q1\tLABEL_TYPO\tFoo Shrine\nQ2\tNOT_A_DEFECT\treason\n",
                   encoding="utf-8")
    assert b.already_handled() == {"Q1", "Q2"}


def test_a_no_statement_decision_still_counts_as_handled(paths):
    """The case a staged-file-only guard would miss, and the one that actually
    occurred: 15 items decided 'not a defect', producing no QS line."""
    log, qs = paths
    log.write_text("Q7\tNOT_A_DEFECT\tlabel and reading are both correct\n",
                   encoding="utf-8")
    qs.write_text("", encoding="utf-8")
    assert "Q7" in b.already_handled()


def test_staged_quickstatements_are_handled(paths):
    _, qs = paths
    qs.write_text('Q3|Len|"Bar Shrine"\n-Q4|Len|"Baz"\n', encoding="utf-8")
    assert b.already_handled() == {"Q3", "Q4"}


def test_both_sources_are_unioned(paths):
    log, qs = paths
    log.write_text("Q1\tOTHER\tnote\n", encoding="utf-8")
    qs.write_text('Q3|Len|"Bar Shrine"\n', encoding="utf-8")
    assert b.already_handled() == {"Q1", "Q3"}


def test_junk_lines_are_ignored(paths):
    log, _ = paths
    log.write_text("\nnot a qid line\nQ9\tOTHER\tfine\n", encoding="utf-8")
    assert b.already_handled() == {"Q9"}
