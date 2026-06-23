"""Tests for select_shrines_to_translate — the LLM must only see the residual
after Stages 0/1/2 (A4): exclude QIDs already in any deterministic en-label file.
Covers both shrines and Japanese Buddhist temples (separate per-kind batches)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import select_shrines_to_translate as s  # noqa: E402


def _write(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def test_excluded_qids_aggregates_across_all_label_files(tmp_path):
    _write(tmp_path / "en_labels_sonnet.txt", ['Q1|Len|"a"'])
    _write(tmp_path / "en_labels.txt", ['Q2|Len|"b"'])
    _write(tmp_path / "kana_en_labels.txt", ['Q3|Len|"c"', 'Q3|Aen|"c2"'])
    _write(tmp_path / "temple_en_labels.txt", ['Q5|Len|"Kinkaku-ji Temple"'])
    _write(tmp_path / "identical_name_en_labels.txt", ['Q4|Len|"d"'])
    assert s.excluded_qids(base=str(tmp_path)) == {"Q1", "Q2", "Q3", "Q4", "Q5"}


def test_temple_label_file_is_excluded():
    assert "temple_en_labels.txt" in s.EXCLUDE_FILES


def test_excluded_qids_missing_files_ok(tmp_path):
    assert s.excluded_qids(base=str(tmp_path)) == set()


def test_select_skips_excluded():
    items = [{"qid": f"Q{i}"} for i in range(1, 6)]
    chosen = s.select(items, {"Q1", "Q2", "Q3"}, count=5)
    assert {c["qid"] for c in chosen} == {"Q4", "Q5"}


def test_select_caps_at_count():
    items = [{"qid": f"Q{i}"} for i in range(1, 20)]
    assert len(s.select(items, set(), count=5)) == 5


# ---- the combined shrine+temple batch ----

def test_select_batches_tags_kinds_and_keeps_both():
    shrines = [{"qid": f"Q{i}"} for i in range(1, 4)]
    temples = [{"qid": f"Q{i}"} for i in range(100, 103)]
    out = s.select_batches(shrines, temples, set(), count=5)
    kinds = {c["qid"]: c["kind"] for c in out}
    assert kinds["Q1"] == "shrine" and kinds["Q100"] == "temple"
    assert len([c for c in out if c["kind"] == "shrine"]) == 3
    assert len([c for c in out if c["kind"] == "temple"]) == 3


def test_select_batches_each_kind_capped_independently():
    shrines = [{"qid": f"Q{i}"} for i in range(1, 20)]
    temples = [{"qid": f"Q{i}"} for i in range(100, 120)]
    out = s.select_batches(shrines, temples, set(), count=5)
    assert len([c for c in out if c["kind"] == "shrine"]) == 5
    assert len([c for c in out if c["kind"] == "temple"]) == 5  # temples don't reduce shrine quota


def test_select_batches_respects_exclude():
    shrines = [{"qid": "Q1"}, {"qid": "Q2"}]
    temples = [{"qid": "Q100"}, {"qid": "Q101"}]
    out = s.select_batches(shrines, temples, {"Q1", "Q100"}, count=5)
    assert {c["qid"] for c in out} == {"Q2", "Q101"}
