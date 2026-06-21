"""Tests for select_shrines_to_translate — the LLM must only see the residual
after Stages 0/1/2 (A4): exclude QIDs already in any deterministic en-label file,
not just en_labels_sonnet.txt."""

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
    _write(tmp_path / "identical_name_en_labels.txt", ['Q4|Len|"d"'])
    assert s.excluded_qids(base=str(tmp_path)) == {"Q1", "Q2", "Q3", "Q4"}


def test_excluded_qids_missing_files_ok(tmp_path):
    assert s.excluded_qids(base=str(tmp_path)) == set()


def test_select_skips_excluded():
    items = [{"qid": f"Q{i}"} for i in range(1, 6)]
    exclude = {"Q1", "Q2", "Q3"}
    chosen = s.select(items, exclude, count=5)
    qids = {c["qid"] for c in chosen}
    assert qids == {"Q4", "Q5"}


def test_select_caps_at_count():
    items = [{"qid": f"Q{i}"} for i in range(1, 20)]
    chosen = s.select(items, set(), count=5)
    assert len(chosen) == 5
