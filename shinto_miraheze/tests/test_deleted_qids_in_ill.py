"""Tests for deleted_qids_in_ill — marking deleted QIDs + self-healing the tag.

Network (wbgetentities) is bypassed by pre-seeding the module-level `_qid_exists`
cache (qid -> True if live, False if deleted).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrators.ops import deleted_qids_in_ill as op  # noqa: E402

TAG = "[[Category:Pages with deleted QID in ill template]]"


def _seed(mapping):
    op._qid_exists.clear()
    op._qid_exists.update(mapping)


def test_deleted_qid_marked_and_tagged():
    _seed({"Q702140": False})
    text = "{{ill|Q702140|qid=Q702140|lt=Ōnamuchi}}\n"
    new, summary = op.apply("Nawino Shrine", text)
    assert "qid=DELETED_QID" in new
    assert TAG in new
    assert "deleted QID" in summary


def test_stale_tag_self_heals():
    # valid qid, no DELETED_QID, but tag present -> tag must be dropped
    _seed({"Q327651": True})
    text = "{{ill|Bathing|en|Bathing|qid=Q327651|lt=bathing}}\n" + TAG + "\n"
    new, summary = op.apply("Bath Additive", text)
    assert new is not None
    assert TAG not in new
    assert "remove stale" in summary


def test_placeholder_keeps_tag():
    # an unresolved DELETED_QID placeholder must NOT be self-healed away
    _seed({"Q327651": True})
    text = "{{ill|Q702140|qid=DELETED_QID|lt=Ōanamuchi}}\n" + TAG + "\n"
    assert op.apply("Ogawa Shrine", text) == (None, None)


def test_all_valid_no_tag_no_change():
    _seed({"Q327651": True})
    text = "{{ill|Bathing|en|Bathing|qid=Q327651|lt=bathing}}\n"
    assert op.apply("Fine Page", text) == (None, None)
