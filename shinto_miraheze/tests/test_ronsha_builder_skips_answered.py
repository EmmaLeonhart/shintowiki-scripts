"""The ronsha builder must not re-queue work the routine has already answered.

Skipping on work-file EXISTENCE alone is not enough. The collector deletes the
file when it answers, and the builder's SPARQL target query reads live Wikidata,
where the ranking is still absent because its QuickStatements line is staged and
has not been applied. So a rebuild re-creates the work-file, the cloud routine
spends one of its handful of daily items re-answering it, and the collector
stages it a second time.

Three of the four builders were fixed for this on 2026-08-04. This one never was,
which did not matter while it only ran by hand — until it was wired into the
daily cleanup-loop on 2026-09-12. A smoke-test run the next morning recreated
five work-files, three of whose answers were already in the staged .txt.

`already_handled()` reads all three records of "done": the staged QuickStatements
file, `_resolved.log`, and `_undecidable.log`. UNDECIDABLE counts — re-asking a
question the routine has declined wastes the same slot as re-asking a settled one.
"""

import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILDER = os.path.join(ROOT, "shinto_miraheze", "build_ronsha_ranking_queue.py")


def _module():
    spec = importlib.util.spec_from_file_location("_brq", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_three_records_of_done_are_consulted():
    mod = _module()
    src = open(BUILDER, encoding="utf-8").read()
    for name in ("QS_OUT", "RESOLVED_LOG", "UNDECIDABLE_LOG"):
        assert name in src, f"{name} is no longer read — that record of 'done' is ignored"
    assert "already_handled" in src
    assert "if qid in handled:" in src, (
        "already_handled() exists but the write loop does not consult it")


def test_a_staged_answer_is_treated_as_done(tmp_path, monkeypatch):
    mod = _module()
    qs = tmp_path / "qualifiers.txt"
    qs.write_text('Q1|P460|Q2|P1352|1\n', encoding="utf-8")
    resolved = tmp_path / "_resolved.log"
    resolved.write_text("Q3\tLIKELY\tQ4\n", encoding="utf-8")
    undecidable = tmp_path / "_undecidable.log"
    undecidable.write_text("Q5\tno candidate preferred\n", encoding="utf-8")
    monkeypatch.setattr(mod, "QS_OUT", str(qs))
    monkeypatch.setattr(mod, "RESOLVED_LOG", str(resolved))
    monkeypatch.setattr(mod, "UNDECIDABLE_LOG", str(undecidable))
    assert mod.already_handled() == {"Q1", "Q3", "Q5"}


def test_missing_records_are_not_an_error(tmp_path, monkeypatch):
    """A fresh checkout has none of the three. That must mean "nothing is done
    yet", not a crash — the builder runs unattended in CI."""
    mod = _module()
    for name in ("QS_OUT", "RESOLVED_LOG", "UNDECIDABLE_LOG"):
        monkeypatch.setattr(mod, name, str(tmp_path / f"absent_{name}"))
    assert mod.already_handled() == set()


def test_the_live_records_still_cover_the_five_that_were_re_queued():
    """The actual incident, pinned against the repo's own state."""
    mod = _module()
    if not os.path.exists(mod.RESOLVED_LOG):
        pytest.skip("no _resolved.log in this checkout")
    handled = mod.already_handled()
    for qid in ("Q135039676", "Q135040696", "Q135041107"):
        assert qid in handled, f"{qid} has a staged answer but would be re-queued"
