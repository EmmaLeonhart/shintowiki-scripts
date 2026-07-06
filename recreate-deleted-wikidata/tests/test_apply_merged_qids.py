"""Unit tests for the pure logic in apply_merged_qids."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apply_merged_qids as a  # noqa: E402


def test_apply_merges_whole_token_only():
    merges = {"Q140446120": "Q11587884"}
    # exact token replaced...
    assert a.apply_merges("qid=Q140446120", merges) == "qid=Q11587884"
    # ...but Q1 must NOT match inside Q140446120, and unmapped QIDs untouched.
    assert a.apply_merges("Q1\tP22\tQ140446120\tQ999", {"Q1": "Q2"}) == "Q2\tP22\tQ140446120\tQ999"


def test_apply_merges_multiple_and_in_context():
    merges = {"Q140446120": "Q11587884", "Q5": "Q5"}
    text = "{{ill|Foo|ja|フー|qid=Q140446120}} and {{ill|Bar|qid=Q140446120|dd=Q1}}"
    out = a.apply_merges(text, merges)
    assert "Q140446120" not in out
    assert out.count("Q11587884") == 2
    assert "dd=Q1" in out   # unrelated QID preserved


def test_load_merges(tmp_path):
    p = tmp_path / "m.txt"
    p.write_text("# comment\nQ140446120\tQ11587884\n\nnot a line\nQ5 Q6\n", encoding="utf-8")
    assert a.load_merges(str(p)) == {"Q140446120": "Q11587884", "Q5": "Q6"}
