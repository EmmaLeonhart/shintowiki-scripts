"""Tests for merged_qids_in_ill — canonicalizing merged (redirected) Wikidata QIDs in ills.

The network resolver is bypassed by pre-seeding the module-level `_merge_target` cache
(qid -> surviving target, or None if canonical).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrators.ops import merged_qids_in_ill as op  # noqa: E402


def _seed(mapping):
    op._merge_target.clear()
    op._merge_target.update(mapping)


def test_rewrites_merged_qid():
    _seed({"Q100": "Q200", "Q200": None})
    new, summary = op.apply("Page", "See {{ill|Foo|ja|フー|qid=Q100}} here.")
    assert "qid=Q200" in new
    assert "Q100" not in new
    assert "Q100→Q200" in summary


def test_follows_redirect_chain():
    _seed({"Q1": "Q2", "Q2": "Q3", "Q3": None})
    new, _ = op.apply("P", "{{ill|X|ja|エックス|qid=Q1}}")
    assert "qid=Q3" in new


def test_canonical_qid_is_noop():
    _seed({"Q5": None})
    assert op.apply("P", "{{ill|X|ja|エックス|qid=Q5}}") == (None, None)


def test_legacy_WD_param_rewritten_to_qid():
    _seed({"Q9": "Q10", "Q10": None})
    new, _ = op.apply("P", "{{ill|X|ja|エックス|WD=Q9}}")
    assert "qid=Q10" in new
    assert "WD=Q9" not in new


def test_no_ill_is_noop():
    assert op.apply("P", "plain text, no ill") == (None, None)


def test_cycle_guard_makes_no_rewrite():
    # a pathological A->B->A cycle must terminate AND not rewrite (the chain
    # resolves back to the original QID, so there is no safe canonical target).
    _seed({"Q1": "Q2", "Q2": "Q1"})
    assert op.apply("P", "{{ill|X|ja|エックス|qid=Q1}}") == (None, None)
