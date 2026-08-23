"""A called workflow that reads `secrets.*` must be passed `secrets:` by its caller.

GitHub does not share secrets with a reusable workflow. A callee's own

    env:
      MIRAHEZE_EMAIL: ${{ secrets.MIRAHEZE_EMAIL }}

resolves to the EMPTY STRING unless the calling job says `secrets: inherit` (or passes
them explicitly). There is no warning and no error at the call — the variable is simply
blank, and whatever reads it decides what happens next.

Found 2026-08-22. `cleanup-loop.yml` calls ~20 reusable workflows; four of them were
missing the line, and two of those four — `generate-quickstatements` and `generate-pages`
— are the whole QuickStatements generation half of the daily pipeline. Since 2026-08-18
the UA builder refuses to construct a User-Agent with no contact address, so from the
next run onward every generator in both jobs died on

    RuntimeError: MIRAHEZE_EMAIL is not set.

`description_label_pairs.txt` had not been regenerated since 2026-08-02 as a result, and
`submit-quickstatements` was skipped every day because its dependency had failed.

The defect is invisible by reading either file alone: the callee names the secret and
looks correct, the caller names the workflow and looks correct. It is only the pairing
that is wrong, which is what this test checks.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WF = os.path.join(_ROOT, ".github", "workflows")

CALL = re.compile(r"uses:\s*\./\.github/workflows/(\S+)")
SECRET = re.compile(r"secrets\.([A-Z0-9_]+)")
PASSES = re.compile(r"^\s*secrets:")


def _workflows():
    return {
        name: open(os.path.join(_WF, name), encoding="utf-8").read()
        for name in sorted(os.listdir(_WF))
        if name.endswith((".yml", ".yaml"))
    }


def _offenders():
    src = _workflows()
    reads = {name: set(SECRET.findall(body)) for name, body in src.items()}
    bad = []
    for caller, body in src.items():
        lines = body.splitlines()
        for i, line in enumerate(lines):
            m = CALL.search(line)
            if not m:
                continue
            callee = m.group(1)
            indent = len(line) - len(line.lstrip())
            passes = False
            for nxt in lines[i + 1:]:
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) < indent:
                    break
                if PASSES.match(nxt):
                    passes = True
                    break
            wanted = reads.get(callee, set())
            if wanted and not passes:
                bad.append("%s:%d calls %s (which reads %s)"
                           % (caller, i + 1, callee, ",".join(sorted(wanted))))
    return bad


def test_every_secret_reading_callee_is_passed_secrets():
    bad = _offenders()
    assert not bad, (
        "these reusable-workflow calls omit `secrets: inherit`, so the callee sees the "
        "secret as an empty string: " + "; ".join(bad))


def test_the_scan_actually_sees_the_calls():
    """Guards against a vacuous pass — an empty or unreadable workflow directory would
    otherwise report zero offenders and read as healthy."""
    src = _workflows()
    assert "cleanup-loop.yml" in src
    calls = [l for l in src["cleanup-loop.yml"].splitlines() if CALL.search(l)]
    assert len(calls) > 10, len(calls)
