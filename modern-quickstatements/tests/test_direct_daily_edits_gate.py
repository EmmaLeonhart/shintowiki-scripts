"""The freshness gate as wired into the only editor that reaches Wikidata.

It must FAIL CLOSED: a gate that opens when its inputs are missing is not a gate,
and a Wikidata API hiccup mid-run is an ordinary failure mode.

The global pause around ブルーノ・プラス was removed 2026-07-21 (Emma's call), so
its tests are gone. Only the per-item rule is wired in now.
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import conflict_gate as cg  # noqa: E402
import direct_daily_edits as dde  # noqa: E402

TODAY = datetime.date(2026, 7, 10)


def test_the_editor_imports_the_gate():
    assert dde.conflict_gate is cg


def test_the_global_pause_is_no_longer_wired_in():
    """Regression guard: the drip must not reacquire a person-specific pause."""
    assert not hasattr(dde, "load_conflict_watch")


# ─────────────────── per-item freshness, fail closed ───────────────────

def test_item_lookup_failure_declines_the_edit(monkeypatch):
    def boom(_qid, **_kw):
        raise RuntimeError("API down")
    monkeypatch.setattr(cg, "fetch_item_revisions", boom)
    ok, why = dde.item_is_editable("Q42", TODAY)
    assert not ok
    assert "lookup failed" in why


def test_item_edited_by_another_user_yesterday_is_declined(monkeypatch):
    monkeypatch.setattr(cg, "fetch_item_revisions",
                        lambda _q, **_k: [("SomeEditor", datetime.date(2026, 7, 9))])
    ok, why = dde.item_is_editable("Q123044569", TODAY)
    assert not ok
    assert "SomeEditor" in why


def test_item_only_we_have_touched_is_editable(monkeypatch):
    monkeypatch.setattr(cg, "fetch_item_revisions",
                        lambda _q, **_k: [("Immanuelle", TODAY)])
    ok, why = dde.item_is_editable("Q42", TODAY)
    assert ok and why is None


def test_item_untouched_for_eight_days_is_editable(monkeypatch):
    monkeypatch.setattr(cg, "fetch_item_revisions",
                        lambda _q, **_k: [("Someone", datetime.date(2026, 7, 2))])
    ok, _ = dde.item_is_editable("Q42", TODAY)
    assert ok
