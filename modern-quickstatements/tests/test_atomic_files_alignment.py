"""Drift guard (2026-07-04): with the QS path retired, direct_daily_edits is
the ONLY road to Wikidata — every file the daily report tracks must be in its
sampling list, or that file's lines silently never flow (exactly what happened
to both temple label files and five others before the retirement)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import direct_daily_edits  # noqa: E402
import submit_daily_batch  # noqa: E402


def test_direct_list_superset_of_report_list():
    missing = set(submit_daily_batch.ATOMIC_FILES) - set(direct_daily_edits.ATOMIC_FILES)
    assert not missing, f"files tracked but never edited: {sorted(missing)}"


def test_retired_report_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "en_labels.txt").write_text("Q1|Len|\"X\"\n", encoding="utf-8")
    report = submit_daily_batch.build_report()
    assert report["outcome"] == "qs_retired"
    by_file = {b["file"]: b for b in report["batches"]}
    assert by_file["en_labels.txt"]["lines_available"] == 1
    assert all(b["lines_submitted"] == 0 for b in report["batches"])
