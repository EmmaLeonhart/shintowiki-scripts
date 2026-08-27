"""CI must run the suite when the suite itself changes.

`ci.yml` is paths-filtered so that orchestrator state-commit churn does not trigger
it. Until 2026-08-27 that filter listed the source trees and `ci.yml` but **not**
`tests/**.py`, so a commit touching only tests ran no tests: `b58dd81f` added a new
test file plus four workflow YAMLs and got no CI run at all. Worse than a missing
signal, it was a misleading one -- every green run up to then happened to be on a
commit that also touched a source tree, so the suite looked gated when it wasn't.

`.github/workflows/**` belongs in the filter for the mirror-image reason:
`test_miraheze_writers_are_lockout_gated` READS the workflow tree, so a workflow
edit changes that test's input. Without the entry, the test guarding the wiki
lockout would never run on the very files it guards.

A paths filter is silent when wrong -- nothing errors, runs simply do not happen --
so it gets a test rather than a comment.
"""
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import pytest  # noqa: E402

yaml = pytest.importorskip("yaml")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CI = os.path.join(_ROOT, ".github", "workflows", "ci.yml")


def _triggers():
    assert os.path.isfile(_CI), "ci.yml is missing"
    with open(_CI, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    # PyYAML parses the bare key `on:` as the boolean True.
    return doc.get("on") or doc.get(True) or {}


def _paths(event):
    trig = _triggers().get(event) or {}
    return list(trig.get("paths") or [])


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_the_suite_runs_when_the_suite_changes(event):
    paths = _paths(event)
    assert paths, f"ci.yml has no paths filter for {event}"
    assert any(p.startswith("tests/") for p in paths), (
        f"ci.yml {event} paths do not include tests/ — a test-only commit would "
        f"run no tests. Got: {paths}"
    )


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_workflow_edits_run_the_test_that_reads_workflows(event):
    paths = _paths(event)
    assert any(p.startswith(".github/workflows/") for p in paths), (
        f"ci.yml {event} paths do not cover .github/workflows/ — "
        f"test_miraheze_writers_are_lockout_gated reads that tree, so a workflow "
        f"edit would not run the test that guards it. Got: {paths}"
    )


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_the_source_trees_are_still_covered(event):
    """Widening the filter must not have dropped what it already had."""
    paths = _paths(event)
    for required in ("shinto_miraheze/**.py", "modern-quickstatements/**.py",
                     "shinto-label-generator/**.py", "recreate-deleted-wikidata/**.py",
                     "jinjacho/**.py"):
        assert required in paths, f"ci.yml {event} lost {required}"


def test_this_test_file_is_itself_covered_by_the_filter():
    """The self-referential check: this file must be able to trigger its own run."""
    rel = os.path.relpath(os.path.abspath(__file__), _ROOT).replace(os.sep, "/")
    assert rel.startswith("tests/") and rel.endswith(".py")
    assert any(p.startswith("tests/") and p.endswith(".py") for p in _paths("push"))
