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
    # The conflict gate (2026-07-10) short-circuits main() before login, so without
    # opening it here every test in this file would pass VACUOUSLY on the gate's
    # `return 0`. These tests are about login and exit-code semantics; the gate has
    # its own tests in test_direct_daily_edits_gate.py and test_conflict_gate.py.
    # Backdating last_edit is NOT enough: MIN_PAUSE_UNTIL is an absolute floor, so
    # the gate stays shut whatever the watched user did. Open it at the seam.
    monkeypatch.setattr(dde.conflict_gate, "pause_reason",
                        lambda *_a, **_k: None)
    # The Wikidata lockout (Emma, 2026-08-18; expired 2026-09-01) short-circuits main() the same
    # way the conflict gate does — earlier, in fact — with `return 0` and a SKIPPED line. Left
    # closed, every test in this file fails on `assert main() == 1` for a reason that has nothing
    # to do with what it tests, and "fixing" that by asserting 0 would make the whole file pass
    # VACUOUSLY forever, re-hiding exactly the 2026-07-06 outage class it exists to catch. So the
    # lockout is opened at the seam, like the gate above; the lockout has its own tests elsewhere.
    monkeypatch.setattr(dde, "wikidata_editing_allowed", lambda *_a, **_k: (True, "test: lockout opened at the seam"))
    monkeypatch.setattr(dde, "item_is_editable", lambda _qid, _today=None: (True, None))
    # The sequential-misc line is woven into every run when sequential_misc.txt has lines
    # (it does in CI, not locally), which added a third edit to two-line tests. These tests
    # are about exit codes and counts, so the sequential file is held empty here.
    monkeypatch.setattr(dde, "load_sequential_lines", lambda *_a, **_k: [])


# test_the_gate_blocks_main_before_login removed 2026-09-27: the conflict_gate global pause it tested was removed (Emma).

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


def test_fail_fast_stops_after_the_first_ten_failures(monkeypatch, tmp_path):
    """Emma 2026-09-27: a run whose first FAIL_FAST_N attempted edits all fail stops
    and reports blocked=true, so wikidata-drip.yml can retry on a fresh runner."""
    _patch_common(monkeypatch)
    lines = [f"Q{i}|P17|Q17" for i in range(1, 40)]
    monkeypatch.setattr(dde, "read_all_lines", lambda: lines)
    monkeypatch.setattr(dde, "wd_login", lambda: ("session", "csrf"))
    calls = {"n": 0}

    def _exec(*a):
        calls["n"] += 1
        return (False, "API error: The save has failed. [failed-save]")

    monkeypatch.setattr(dde, "execute_line", _exec)
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert dde.main() == 1
    assert calls["n"] == dde.FAIL_FAST_N
    assert "blocked=true" in out.read_text(encoding="utf-8")


def test_already_there_lines_do_not_count_toward_fail_fast(monkeypatch, tmp_path):
    _patch_common(monkeypatch)
    lines = [f"Q{i}|P17|Q17" for i in range(1, 25)]
    monkeypatch.setattr(dde, "read_all_lines", lambda: lines)
    monkeypatch.setattr(dde, "wd_login", lambda: ("session", "csrf"))
    monkeypatch.setattr(dde, "execute_line", lambda *a: (True, "Skipped (already exists)"))
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    dde.main()
    text = out.read_text(encoding="utf-8")
    assert "blocked=false" in text and "landed=0" in text


def test_a_good_run_reports_what_landed(monkeypatch, tmp_path):
    _patch_common(monkeypatch)
    monkeypatch.setattr(dde, "read_all_lines", lambda: ["Q1|P17|Q17", "Q2|P17|Q17"])
    monkeypatch.setattr(dde, "wd_login", lambda: ("session", "csrf"))
    monkeypatch.setattr(dde, "execute_line", lambda *a: (True, "Created"))
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert dde.main() == 0
    assert "landed=2" in out.read_text(encoding="utf-8")
