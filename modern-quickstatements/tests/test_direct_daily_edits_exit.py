"""Exit-code behavior for direct_daily_edits.main() (queue #10 reliability fix).

The 2026-07-06 outage (an invalidated bot token failing every save) hid behind a
green run for days because main() exited 0 regardless. main() must now return
non-zero on login failure and on total edit failure, 0 otherwise.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import direct_daily_edits as dde  # noqa: E402


def _patch_common(monkeypatch):
    monkeypatch.setattr(dde.time, "sleep", lambda *_: None)
    monkeypatch.setattr(dde.random, "sample", lambda pop, k: list(pop)[:k])
    # The global pause that used to short-circuit main() before login was removed
    # 2026-07-21, so there is no longer a gate to open here. The per-item freshness
    # gate still runs inside the edit loop; open it so these tests exercise login
    # and exit-code semantics rather than the gate (which has its own tests in
    # test_direct_daily_edits_gate.py and test_conflict_gate.py).
    monkeypatch.setattr(dde, "item_is_editable", lambda _qid, _today=None: (True, None))


def test_empty_backlog_returns_0(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(dde, "read_all_lines", lambda: [])
    assert dde.main() == 0


def test_login_failure_returns_1(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(dde, "read_all_lines", lambda: ["Q1|P17|Q17"])
    monkeypatch.setattr(dde, "wd_login", lambda: (None, None))
    assert dde.main() == 1


def test_total_failure_returns_1(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(dde, "read_all_lines", lambda: ["Q1|P17|Q17", "Q2|P17|Q17"])
    monkeypatch.setattr(dde, "wd_login", lambda: ("session", "csrf"))
    monkeypatch.setattr(dde, "execute_line", lambda *a: (False, "The save has failed."))
    assert dde.main() == 1


def test_some_success_returns_0(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(dde, "read_all_lines", lambda: ["Q1|P17|Q17", "Q2|P17|Q17"])
    monkeypatch.setattr(dde, "wd_login", lambda: ("session", "csrf"))
    calls = {"n": 0}

    def _exec(*a):
        calls["n"] += 1
        return (calls["n"] == 1, "Created" if calls["n"] == 1 else "fail")

    monkeypatch.setattr(dde, "execute_line", _exec)
    assert dde.main() == 0
