"""The 2026-08-06 editing hold must outrank every date-based unlock.

Emma set a CONDITION, not a date: no shintowiki editing until "Immanuelle" is no
longer mentioned on [[Wikipedia:AI noticeboard]] or [[Wikipedia talk:WikiProject
Japan]]. The pre-existing machinery only understood dates — `locked_until` expires
on its own, and a passing weekly edit-test rewrites the state to `locked: false`.
Either would have quietly reopened editing while the condition still held, which is
the exact failure these tests exist to catch.
"""
import datetime
import importlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

wea = importlib.import_module("shinto_miraheze.wiki_edit_allowed")

HOLD = {
    "hold": True,
    "set": "2026-08-06",
    "set_by": "Emma",
    "release_condition": "no editing until the enwiki mentions clear",
}


def _state(tmp_path, monkeypatch, payload):
    p = tmp_path / "wiki_editing_lockout.state"
    p.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(wea, "STATE_PATH", p)
    return p


def _days(n):
    # ±3 days, because the guard compares against the UTC date while the test host
    # may be hours behind it — ±1 straddles the boundary in the Vancouver evening.
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()


def test_hold_blocks_even_when_the_date_lock_has_expired(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch, {"locked": True, "locked_until": _days(-3),
                                   "editing_hold": HOLD})
    allowed, detail = wea.editing_allowed()
    assert not allowed
    assert "HELD" in detail


def test_hold_blocks_even_when_the_state_says_unlocked(tmp_path, monkeypatch):
    # This is the weekly-edit-test-passes case: locked False, hold still standing.
    _state(tmp_path, monkeypatch, {"locked": False, "locked_until": None,
                                   "editing_hold": HOLD})
    allowed, _ = wea.editing_allowed()
    assert not allowed


def test_no_hold_leaves_the_old_date_behaviour_untouched(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch, {"locked": True, "locked_until": _days(3)})
    assert not wea.editing_allowed()[0]

    _state(tmp_path, monkeypatch, {"locked": True, "locked_until": _days(-3)})
    assert wea.editing_allowed()[0]

    _state(tmp_path, monkeypatch, {"locked": False})
    assert wea.editing_allowed()[0]


def test_hold_false_is_not_a_hold(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch, {"locked": False,
                                   "editing_hold": {"hold": False, "set": "x"}})
    assert wea.editing_allowed()[0]


def test_weekly_test_carries_the_hold_across_a_state_rewrite(tmp_path, monkeypatch):
    wt = importlib.import_module("shinto_miraheze.weekly_wiki_edit_test")
    p = tmp_path / "wiki_editing_lockout.state"
    p.write_text(json.dumps({"locked": True, "locked_until": "2026-08-10",
                             "editing_hold": HOLD}), encoding="utf-8")
    monkeypatch.setattr(wt, "STATE", p)
    monkeypatch.setattr(wt, "QUEUE", tmp_path / "queue.md")

    now = datetime.datetime(2026, 8, 12, tzinfo=datetime.timezone.utc)
    st = wt.write_state(True, "simulated pass", now)   # the unlock path
    assert st["locked"] is False                        # date lock lifted, as before
    assert st["editing_hold"] == HOLD                   # but the hold survives
    assert json.loads(p.read_text(encoding="utf-8"))["editing_hold"] == HOLD


def test_live_state_file_has_the_hold_in_force():
    """Guards against a future rewrite silently dropping Emma's hold."""
    live = json.loads((pathlib.Path(__file__).resolve().parents[1]
                       / "wiki_editing_lockout.state").read_text(encoding="utf-8"))
    hold = live.get("editing_hold")
    if hold is None:
        # Lifting the hold is a deliberate human act; once it is gone this test
        # has nothing to guard.
        return
    assert hold["hold"] is True
    assert hold["release_condition"]
