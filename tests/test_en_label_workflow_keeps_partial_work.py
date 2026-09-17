"""A 429 bail must not discard the work the earlier steps already did — and must
still go red.

`generate-shrines-missing-en-label.yml` runs eight generators and commits their
output in a LATER step. On 2026-09-16 and 2026-09-17 the temple Stage 2 query (the
biggest of the run, ~6,114 distinct ja labels) got an HTTP 429 and bailed. Bailing
on 429 is correct repo policy -- but because the commit sat behind it, five steps
that had already succeeded had their output computed and thrown away, both days.
The last refresh on main was 2026-09-15.

The obvious fix is the one the sibling workflow already made, and it is a trap.
`generate-quickstatements.yml` marks its generators `continue-on-error: true` with
nothing re-failing the job, so a 429 reports GREEN and the file silently stops
regenerating: `description_label_pairs.txt` sat unchanged from 2026-08-02 through
three Sundays and nothing ever looked wrong (that workflow's own line-36 comment).

So the invariant has TWO halves and neither is safe alone:
  * every generation step continues past a bail, so the commit still runs; and
  * a final step re-fails the job, so the bail stays visible.

Both are silent when wrong -- half one missing loses a day's work with a red X that
looks like an ordinary outage, half two missing loses the signal entirely -- which
is why this is a test and not a comment.
"""
import os

import pytest

yaml = pytest.importorskip("yaml")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WF = os.path.join(_ROOT, ".github", "workflows",
                   "generate-shrines-missing-en-label.yml")

# The generation steps, by id. Each writes a file the commit step stages.
_GENERATORS = [
    "gen_shrines", "gen_kana", "gen_identical", "gen_temples",
    "gen_temple_en", "gen_temple_identical", "gen_dedup", "gen_cjk",
]


def _steps():
    assert os.path.isfile(_WF), "generate-shrines-missing-en-label.yml is missing"
    with open(_WF, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["jobs"]["generate"]["steps"]


def _by_id():
    return {s["id"]: s for s in _steps() if s.get("id")}


@pytest.mark.parametrize("step_id", _GENERATORS)
def test_every_generation_step_continues_past_a_bail(step_id):
    step = _by_id().get(step_id)
    assert step is not None, (
        f"{step_id} is gone from the workflow. If a generator was renamed or "
        f"removed, update _GENERATORS and the re-fail step together."
    )
    assert step.get("continue-on-error") is True, (
        f"{step_id} is not continue-on-error, so a 429 there discards the output "
        f"of every step before it -- the 2026-09-16/17 failure."
    )


def test_a_final_step_re_fails_the_job():
    steps = _steps()
    last = steps[-1]
    assert "re-fail" in last["name"].lower(), (
        f"the last step is {last['name']!r}, not the re-fail guard. It must be "
        f"last and after the commit: commit what succeeded, then go red anyway."
    )
    assert last.get("if") == "always()", (
        "the re-fail step must run with if: always(), or it is skipped in exactly "
        "the case it exists for."
    )
    assert last.get("continue-on-error") is not True, (
        "the re-fail step must not be continue-on-error -- that restores the "
        "sibling workflow's silent-green fault."
    )


def test_the_re_fail_step_checks_every_generator():
    last = _steps()[-1]
    run = last["run"]
    for step_id in _GENERATORS:
        assert f"steps.{step_id}.outcome" in run, (
            f"the re-fail step never reads steps.{step_id}.outcome, so that "
            f"generator can fail silently and the job stays green."
        )
    assert "exit 1" in run, "the re-fail step never actually fails the job"


def test_the_commit_runs_before_the_re_fail_and_after_the_generators():
    names = [s.get("name", "") for s in _steps()]
    commit = next(i for i, n in enumerate(names) if n.startswith("Commit"))
    ids = [s.get("id") for s in _steps()]
    assert commit > max(ids.index(g) for g in _GENERATORS), (
        "the commit must come after the generators"
    )
    assert commit == len(names) - 2, (
        "the commit must be second-to-last, immediately before the re-fail step "
        "-- otherwise work that succeeded is still not committed."
    )


def test_strip_husk_lines_still_hard_fails():
    """Its own comment: if it cannot run, husk lines stay staged."""
    step = next(s for s in _steps() if "husk" in s.get("name", "").lower())
    assert step.get("continue-on-error") is not True, (
        "strip_husk_lines.py must keep hard-failing -- softening it lets "
        "QuickStatements targeting repurposed husks reach the staged .txt files."
    )
