"""No workflow may fail silently behind `continue-on-error`.

`continue-on-error: true` reports a failed step's CONCLUSION as success. Only its
OUTCOME says it failed, and the outcome is visible nowhere outside the job: not on
the run page, not in `gh run view --json jobs`, not in the REST API. So a job with
tolerant steps and nothing reading their outcomes reads green while losing work:
`label-generator-regenerate.yml` for two days in August 2026 and again on
2026-09-21 (run 35682528723, 39 of 57 languages never ran); `generate-quickstatements`
on 2026-09-26 (Shinmei ids and the kana ADD both died, green); the ontology census on
2026-09-01 (a 502, green).

The campaign (Emma, 2026-09-21: "We run a campaign to fix it") keeps per-step
isolation and adds one shared re-fail step, `shinto_miraheze/refail_failed_steps.py`.
This test sweeps EVERY workflow, so a new tolerant step or a new workflow is covered
without anyone remembering to add it here.
"""
import glob
import os
import sys

import pytest

yaml = pytest.importorskip("yaml")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WF_DIR = os.path.join(_ROOT, ".github", "workflows")
sys.path.insert(0, os.path.join(_ROOT, "shinto_miraheze"))

import refail_failed_steps as rf  # noqa: E402

HELPER = "refail_failed_steps.py"


def _jobs_with_tolerant_steps():
    out = []
    for path in sorted(glob.glob(os.path.join(_WF_DIR, "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            wf = yaml.safe_load(fh)
        for job_name, job in (wf.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any(s.get("continue-on-error") for s in steps):
                out.append((os.path.basename(path), job_name, job, steps, wf["jobs"]))
    return out


JOBS = _jobs_with_tolerant_steps()
IDS = [f"{f}:{j}" for f, j, *_ in JOBS]


def test_the_sweep_finds_the_known_workflows():
    found = {f for f, *_ in JOBS}
    for f in ("generate-quickstatements.yml", "label-generator-regenerate.yml",
              "generate-pages.yml", "ontology-census.yml"):
        assert f in found, f"{f} no longer has tolerant steps; update this test"


@pytest.mark.parametrize("wf,job,jobdef,steps,alljobs", JOBS, ids=IDS)
def test_every_tolerant_step_has_an_id(wf, job, jobdef, steps, alljobs):
    # Only id'd steps appear in the `steps` context, so an id-less tolerant step is
    # invisible to the re-fail step.
    missing = [s.get("name") for s in steps if s.get("continue-on-error") and not s.get("id")]
    assert not missing, f"{wf} [{job}]: tolerant steps with no id: {missing}"


@pytest.mark.parametrize("wf,job,jobdef,steps,alljobs", JOBS, ids=IDS)
def test_the_last_step_re_fails_from_step_outcomes(wf, job, jobdef, steps, alljobs):
    last = steps[-1]
    assert HELPER in (last.get("run") or ""), (
        f"{wf} [{job}]: the last step is {last.get('name')!r}, not the re-fail step. "
        f"It must be last so everything above has already run and committed."
    )
    assert last.get("if") == "always()", f"{wf} [{job}]: the re-fail step needs if: always()"
    assert not last.get("continue-on-error"), f"{wf} [{job}]: the re-fail step is itself tolerant"
    env = last.get("env") or {}
    assert env.get("STEPS_JSON", "").replace(" ", "") == "${{toJSON(steps)}}", (
        f"{wf} [{job}]: STEPS_JSON must be the whole steps context"
    )


@pytest.mark.parametrize("wf,job,jobdef,steps,alljobs", JOBS, ids=IDS)
def test_exemptions_name_real_tolerant_steps(wf, job, jobdef, steps, alljobs):
    env = steps[-1].get("env") or {}
    tolerant = {s.get("id") for s in steps if s.get("continue-on-error")}
    for sid in (env.get("REFAIL_EXEMPT") or "").split():
        assert sid in tolerant, f"{wf} [{job}]: exempt id {sid!r} is not a tolerant step"


@pytest.mark.parametrize("wf,job,jobdef,steps,alljobs", JOBS, ids=IDS)
def test_report_only_is_followed_by_a_job_that_goes_red(wf, job, jobdef, steps, alljobs):
    env = steps[-1].get("env") or {}
    if env.get("REFAIL_REPORT_ONLY") != "1":
        return
    sid = steps[-1].get("id")
    outputs = jobdef.get("outputs") or {}
    out_name = next((k for k, v in outputs.items() if f"steps.{sid}.outputs.failed" in str(v)), None)
    assert out_name, f"{wf} [{job}]: report-only step's result is not a job output"
    followers = [
        n for n, j in alljobs.items()
        if job in (j.get("needs") if isinstance(j.get("needs"), list) else [j.get("needs")])
        and f"needs.{job}.outputs.{out_name}" in str(j)
        and "exit 1" in str(j)
    ]
    assert followers, f"{wf} [{job}]: nothing reads {out_name} and goes red"


def test_the_label_generator_blind_spot_is_closed():
    """The workflow the campaign is named after: none of its pipelines may be exempt."""
    (_, _, _, steps, _), = [j for j in JOBS if j[0] == "label-generator-regenerate.yml"]
    exempt = ((steps[-1].get("env") or {}).get("REFAIL_EXEMPT") or "").split()
    assert exempt == [], f"label-generator pipelines exempted from the re-fail: {exempt}"


def test_the_drip_runs_first_and_generation_only_after_it_landed_edits():
    """wikidata-drip.yml (Emma, 2026-09-27): drip first from the committed files;
    the 80-minute generation only after a drip that landed edits; a blocked drip
    retries on a fresh runner."""
    with open(os.path.join(_WF_DIR, "wikidata-drip.yml"), encoding="utf-8") as fh:
        jobs = yaml.safe_load(fh)["jobs"]
    assert "needs" not in jobs["direct-daily-edits"], "the drip must not wait on generation"
    gen = jobs["generate-quickstatements"]
    assert "direct-daily-edits" in gen["needs"]
    assert "outputs.landed" in str(gen.get("if")), "generation must be gated on edits landing"
    retry = jobs["retry-on-fresh-runner"]
    assert "outputs.blocked == 'true'" in str(retry.get("if"))
    assert "gh workflow run wikidata-drip.yml" in retry["steps"][-1]["run"]

# --- the helper itself -------------------------------------------------------

def test_helper_reads_outcome_not_conclusion():
    steps = {
        "a": {"outcome": "failure", "conclusion": "success"},   # the hidden failure
        "b": {"outcome": "success", "conclusion": "success"},
        "c": {"outcome": "skipped", "conclusion": "skipped"},
    }
    assert rf.failed_steps(steps) == (["a"], [])


def test_helper_exemption_downgrades_but_still_reports():
    steps = {"dl": {"outcome": "failure"}, "gen": {"outcome": "failure"}}
    assert rf.failed_steps(steps, ["dl"]) == (["gen"], ["dl"])


def test_helper_exit_codes(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv("STEPS_JSON", json.dumps({"x": {"outcome": "failure"}}))
    monkeypatch.delenv("REFAIL_EXEMPT", raising=False)
    monkeypatch.delenv("REFAIL_REPORT_ONLY", raising=False)
    assert rf.main() == 1
    monkeypatch.setenv("REFAIL_EXEMPT", "x")
    assert rf.main() == 0
    monkeypatch.delenv("REFAIL_EXEMPT")
    out = tmp_path / "out"
    monkeypatch.setenv("REFAIL_REPORT_ONLY", "1")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert rf.main() == 0
    assert out.read_text(encoding="utf-8") == "failed=x\n"
