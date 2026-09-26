#!/usr/bin/env python3
"""Re-fail a job whose `continue-on-error` steps failed. Runs as the LAST step.

`continue-on-error: true` rewrites a failed step's CONCLUSION to success and leaves
its OUTCOME as failure. The run page, `gh run view --json jobs` and `--log-failed`
all read the conclusion, so a job can lose most of its work and still read green.
`label-generator-regenerate.yml` did exactly that for two days in August 2026, and
again on 2026-09-21 (run 35682528723: 39 of 57 languages never ran, and the run was
green). The REST API does not expose `outcome` at all, so nothing outside the run can
catch this. The only place outcomes are visible is the `steps` context, inside the job.

So the pattern (first built bespoke in generate-shrines-missing-en-label.yml) is:
keep per-step isolation so one broken generator does not stop the others, commit
what succeeded, and then turn the job red here if anything failed.

Usage, as the final step of a job:

    - name: Re-fail if any tolerant step failed
      if: always()
      env:
        STEPS_JSON: ${{ toJSON(steps) }}
        REFAIL_EXEMPT: "download-qs"      # optional, space-separated step ids
      run: python3 shinto_miraheze/refail_failed_steps.py

Only steps with an `id:` appear in the `steps` context, which is why every
`continue-on-error` step must carry one (pinned by
tests/test_continue_on_error_refail.py).

REFAIL_EXEMPT is for steps whose failure is part of their design: a step with an
explicit fallback step behind it, or one that exits 1 on purpose as a signal. An
exempt failure is still printed, as a warning, and does not turn the job red.

REFAIL_REPORT_ONLY=1 is for a job whose own failure would skip a job that needs it
(generate-pages: a red `build` skips `deploy`, so one failed report table would stop
the whole site publishing). In that mode the failed ids are written to
$GITHUB_OUTPUT as `failed=<ids>` and this exits 0; a separate job that runs after
the dependent one reads that output and goes red.

Exit 0 = every tolerant step succeeded (or only exempt ones failed), or report-only.
Exit 1 = at least one non-exempt step's outcome was failure.
"""
import json
import os
import sys


def failed_steps(steps, exempt=()):
    """(failed, exempt_failed) — lists of step ids whose OUTCOME is failure."""
    exempt = set(exempt)
    failed, excused = [], []
    for sid, info in (steps or {}).items():
        if (info or {}).get("outcome") != "failure":
            continue
        (excused if sid in exempt else failed).append(sid)
    return failed, excused


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        steps = json.loads(os.environ.get("STEPS_JSON") or "{}")
    except ValueError as e:
        print(f"::error::STEPS_JSON is not JSON ({e}) — cannot tell what failed")
        return 1
    exempt = (os.environ.get("REFAIL_EXEMPT") or "").split()
    failed, excused = failed_steps(steps, exempt)

    for sid in excused:
        print(f"::warning::{sid} failed (exempt: it has a fallback or fails by design)")
    for sid in failed:
        print(f"::error::{sid} failed (step outcome: failure, hidden by continue-on-error)")

    if os.environ.get("REFAIL_REPORT_ONLY") == "1":
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as fh:
                fh.write("failed=" + " ".join(failed) + "\n")
        print("Report-only: a later job turns the run red if this is non-empty.")
        return 0

    if failed:
        print("Everything that ran after these steps still ran, and anything the job commits "
              "was committed. Failed: " + " ".join(failed))
        return 1
    print(f"No tolerant step failed ({len(steps)} steps with ids checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
