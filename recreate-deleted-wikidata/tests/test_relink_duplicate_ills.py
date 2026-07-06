"""Unit tests for the pure logic in relink_duplicate_ills."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import relink_duplicate_ills as r  # noqa: E402


def test_relink_ill_swaps_qid_and_drops_dd():
    got = r.relink_ill("herbal baths|ja|薬湯|qid=DELETED_QID|dd=Q9999", "Q16496694")
    assert got == "herbal baths|ja|薬湯|qid=Q16496694"


def test_relink_ill_without_dd():
    got = r.relink_ill("Akama Shrine|qid=DELETED_QID", "Q712617")
    assert got == "Akama Shrine|qid=Q712617"


def test_relink_ill_preserves_other_params():
    got = r.relink_ill("Foo|ja|フー|12=simple|13=User:Immanuelle/Foo|qid=DELETED_QID|dd=Q1",
                       "Q42")
    assert "qid=Q42" in got
    assert "dd=" not in got
    assert "13=User:Immanuelle/Foo" in got   # unrelated params untouched


def test_title_to_filename_encodes_forbidden_chars():
    # must match sync_git_synced_pages.title_to_filename so the sync maps file<->title.
    assert r.title_to_filename('Why am I me?') == "Why am I me%3F.wiki"
    assert r.title_to_filename('List "X"') == "List %22X%22.wiki"
    assert r.title_to_filename("Plain Title") == "Plain Title.wiki"
    assert r.title_to_filename("100%") == "100%25.wiki"   # % itself is encoded
