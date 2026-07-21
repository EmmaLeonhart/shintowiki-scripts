"""The caution gate as wired into the only editor that reaches Wikidata.

Both gates must FAIL CLOSED. A caution gate that opens when its inputs are missing
is not a caution gate — and the failure modes here are ordinary (a watcher step that
didn't run, a Wikidata API hiccup mid-run).
"""
import datetime
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import conflict_gate as cg  # noqa: E402
import direct_daily_edits as dde  # noqa: E402

TODAY = datetime.date(2026, 7, 10)


def test_the_editor_imports_the_gate():
    assert dde.conflict_gate is cg


# ─────────────────────── gate 1: global pause, fail closed ───────────────────────

def test_missing_state_file_fails_closed(tmp_path, monkeypatch):
    """No state -> assume they edited today -> drip stays shut."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dde.os.path, "dirname", lambda _p: str(tmp_path))
    watch = dde.load_conflict_watch()
    assert watch["last_edit"] == datetime.datetime.now(datetime.timezone.utc).date()
    # Since HARD_RESUME moved to 2026-07-01 this no longer shuts the drip on its
    # own — only a recorded attention signal does.
    assert cg.should_run(watch["last_edit"], watch["last_edit"])
    assert watch["project_chat_hold"] is False


def test_corrupt_state_file_fails_closed(tmp_path, monkeypatch):
    (tmp_path / "conflict_watch.state").write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(dde.os.path, "dirname", lambda _p: str(tmp_path))
    watch = dde.load_conflict_watch()
    assert watch["last_edit"] == datetime.datetime.now(datetime.timezone.utc).date()


def test_valid_state_file_is_read(tmp_path, monkeypatch):
    (tmp_path / "conflict_watch.state").write_text(
        json.dumps({"last_watched_edit": "2026-07-10",
                    "talk_activity": "2026-04-24",
                    "noticeboard_mention": None,
                    "project_chat_hold": False}),
        encoding="utf-8")
    monkeypatch.setattr(dde.os.path, "dirname", lambda _p: str(tmp_path))
    watch = dde.load_conflict_watch()
    assert watch["last_edit"] == datetime.date(2026, 7, 10)
    assert watch["talk_activity"] == datetime.date(2026, 4, 24)
    assert watch["noticeboard_mention"] is None
    assert watch["project_chat_hold"] is False


def test_project_chat_hold_is_read_and_blocks_indefinitely(tmp_path, monkeypatch):
    (tmp_path / "conflict_watch.state").write_text(
        json.dumps({"last_watched_edit": "2023-03-17", "project_chat_hold": True}),
        encoding="utf-8")
    monkeypatch.setattr(dde.os.path, "dirname", lambda _p: str(tmp_path))
    watch = dde.load_conflict_watch()
    assert watch["project_chat_hold"] is True
    assert not cg.should_run(datetime.date(2030, 1, 1), watch["last_edit"],
                             project_chat_hold=True)


def test_the_drip_is_paused_with_the_real_current_state():
    """The cap is past, so only attention pauses us now."""
    assert cg.should_run(TODAY, datetime.date(2026, 7, 10))
    assert not cg.should_run(TODAY, datetime.date(2026, 7, 10),
                             noticeboard_mention=datetime.date(2026, 7, 9))


# ─────────────────────── gate 2: per-item freshness, fail closed ───────────────────────

def test_item_lookup_failure_declines_the_edit(monkeypatch):
    def boom(_qid, **_kw):
        raise RuntimeError("API down")
    monkeypatch.setattr(cg, "fetch_item_revisions", boom)
    ok, why = dde.item_is_editable("Q42", TODAY)
    assert not ok
    assert "lookup failed" in why


def test_item_edited_by_another_user_yesterday_is_declined(monkeypatch):
    monkeypatch.setattr(cg, "fetch_item_revisions",
                        lambda _q, **_k: [("ブルーノ・プラス", datetime.date(2026, 7, 9))])
    ok, why = dde.item_is_editable("Q123044569", TODAY)
    assert not ok
    assert "ブルーノ・プラス" in why


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


def test_the_two_damaged_items_would_be_declined_today(monkeypatch):
    """Q28069431 and Q123044569 are exactly what the gate exists to protect."""
    monkeypatch.setattr(cg, "fetch_item_revisions",
                        lambda _q, **_k: [("ブルーノ・プラス", datetime.date(2026, 7, 10))])
    for qid in ("Q28069431", "Q123044569"):
        ok, _ = dde.item_is_editable(qid, TODAY)
        assert not ok, qid
