"""Unit tests for build_item_json.build_record — the pure per-QID merge/flag logic."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_item_json as bij


def _rag(qid, bucket, content_was="", **kw):
    return {"qid": qid, "bucket": bucket, "content_was": content_was,
            "del_ts": "20250802042958", "size": 311, "admin": "Xezbeth",
            "comment": "c", "ill_recovered": kw.get("ill_recovered", False),
            "ill_labels": kw.get("ill_labels", [])}


def test_self_deleted_flagged_and_not_candidate():
    for bucket in ("author-request", "batch-improperly-created"):
        rec = bij.build_record(_rag("Q1", bucket), {"matched": True, "langlinks": {"ja": "x"}})
        assert rec["self_deleted"] is True
        assert rec["recreation_candidate"] is False  # own deletion — never a candidate


def test_matched_with_langlinks_is_candidate():
    cross = {"matched": True, "label": "Foo", "fandom_page": "P", "host_pages": ["P"],
             "langlinks": {"ja": "フー"}, "recovered_qid": "Q1", "qid_source": "current-ill",
             "qid_matches_rag": True, "ja_sitelink": None, "categories": ["Kami"],
             "current_ill_qid": "Q1"}
    rec = bij.build_record(_rag("Q1", "empty-item", content_was="Foo"), cross)
    assert rec["recreation_candidate"] is True
    assert rec["fandom"]["langlinks"] == {"ja": "フー"}
    assert rec["recovered_label"] == "Foo"


def test_rfd_no_evidence_not_candidate():
    cross = {"matched": True, "langlinks": {"ja": "x"}, "label": "L"}
    rec = bij.build_record(_rag("Q1", "rfd-no-evidence"), cross)
    assert rec["recreation_candidate"] is False  # editors judged it non-existent


def test_unmatched_has_null_fandom():
    rec = bij.build_record(_rag("Q1", "empty-item"), None)
    assert rec["fandom"] is None
    assert rec["recreation_candidate"] is False


def test_matched_no_langlinks_not_candidate():
    rec = bij.build_record(_rag("Q1", "empty-item"), {"matched": True, "langlinks": {}})
    assert rec["recreation_candidate"] is False  # matched but no recoverable content
