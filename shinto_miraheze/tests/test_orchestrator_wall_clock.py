"""Wall-clock self-stop for the orchestrator loop (added 2026-07-06).

The category orchestrator was timing out at the 160-min CI step limit — killed
red, mid-page, and on a stall with nothing committed — because the only stop
conditions were page-count / edit-count, which can't bound wall-clock when
per-page cost varies (heavy history-offload / fandom-mirror / wikidata-lookup
ops made 1000 category pages take 2h40m). MAX_RUN_SECONDS stops the walk
cleanly BEFORE the CI kill so the run exits green and resumes next fire.

These tests drive run_orchestrator with everything network-touching stubbed,
so only the loop's stop/clear logic is exercised.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shinto_miraheze.orchestrators import common  # noqa: E402


def _dummy_op():
    op = types.SimpleNamespace()
    op.NAME = "dummy"
    op.NAMESPACES = {14}
    op.apply = lambda title, text: (None, None)
    return op


def _stub_walk(monkeypatch, titles, cleared):
    """Stub out every network entry point so run_orchestrator exercises only
    the pure loop logic. Records clear_state calls into `cleared`."""
    monkeypatch.setattr(common, "login_site", lambda: object())
    monkeypatch.setattr(common, "load_state", lambda path: set())
    monkeypatch.setattr(common, "_namespace_prefix", lambda site, ns: "Category:")
    monkeypatch.setattr(common, "_compute_apfrom", lambda done, prefix: "")
    monkeypatch.setattr(common, "iter_allpages",
                        lambda site, ns, start_from="": iter(titles))
    monkeypatch.setattr(common, "clear_state", lambda path: cleared.append(path))
    # faulthandler timer would otherwise linger after the test process.
    import faulthandler
    monkeypatch.setattr(faulthandler, "dump_traceback_later", lambda *a, **k: None)


def test_wall_clock_stops_before_processing_any_page(monkeypatch):
    # Deadline of 0s: the very first loop iteration is past-budget, so the walk
    # stops before touching site.pages at all.
    cleared = []
    _stub_walk(monkeypatch, ["Category:A", "Category:B", "Category:C"], cleared)
    monkeypatch.setattr(common, "MAX_RUN_SECONDS", 0)

    edited, finished_all = common.run_orchestrator(
        namespace=14, ns_label="category", ops=[_dummy_op()],
        state_name="unit_test_orch", apply=True, max_edits=100, run_tag="[[t]]",
    )
    assert edited == 0
    # A deadline stop is a mid-cycle stop, so state must NOT be cleared —
    # the next fire resumes from the cursor.
    assert finished_all is False
    assert cleared == [], "deadline stop must not clear state (would lose the cursor)"


def test_no_deadline_lets_cycle_complete_and_clears(monkeypatch):
    # Generous deadline + an all-no-op op that touches no page text: the walk
    # exhausts and clears state (cycle complete).
    cleared = []
    _stub_walk(monkeypatch, [], cleared)  # empty namespace = immediate exhaust
    monkeypatch.setattr(common, "MAX_RUN_SECONDS", 10_000)

    edited, finished_all = common.run_orchestrator(
        namespace=14, ns_label="category", ops=[_dummy_op()],
        state_name="unit_test_orch", apply=True, max_edits=100, run_tag="[[t]]",
    )
    assert edited == 0
    assert finished_all is True
    assert len(cleared) == 1, "a fully-walked cycle should clear state exactly once"


def test_max_run_seconds_reads_env(monkeypatch):
    # The module default is 145 min; the override env var is honoured on reload.
    import importlib
    monkeypatch.setenv("ORCHESTRATOR_MAX_SECONDS", "1234")
    importlib.reload(common)
    try:
        assert common.MAX_RUN_SECONDS == 1234
    finally:
        monkeypatch.delenv("ORCHESTRATOR_MAX_SECONDS", raising=False)
        importlib.reload(common)
        assert common.MAX_RUN_SECONDS == 145 * 60
