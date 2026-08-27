"""Every workflow step that edits shinto.miraheze.org must respect the lockout.

The miraheze lockout exists so that when the wiki is throwing anti-DDoS 403s we
stop hitting it -- `wiki-editing-lockout.yml` writes a 7-day lockout when the ~1AM
check sees no EmmaBot edits in 8h, and every writer is supposed to consult
`wiki_edit_allowed.py` before touching the wiki. A workflow that skips the guard
keeps editing straight through a blackout, which is precisely the failure a single
state file was introduced to make impossible.

Four workflows were missing it on 2026-08-27 -- `dedupe-duplicate-qids`,
`sunset-jp-char-count-cats`, `sunset-templates-not-transcluded-in-mainspace-cat`
and `tag-templates-not-transcluded-anywhere`. A grep found them; only a test keeps
the next one from being written.

This is deliberately mechanical rather than an allowlist: it reads each step's own
command, resolves the scripts it runs, and asks whether any of them targets
shinto.miraheze. Wikidata writers are correctly out of scope -- they answer to
`wikidata_edit_allowed.py` and a separate state file. Two wikis, two gates.
"""
import os
import re
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
_WORKFLOWS = os.path.join(_ROOT, ".github", "workflows")

SCRIPT_RE = re.compile(r"([\w./-]*shinto_miraheze/[\w_]+\.py)")
MIRAHEZE_TARGET_RE = re.compile(r'WIKI_URL\s*=\s*["\']shinto\.miraheze\.org')
GUARD = "wiki_edit_allowed.py"


def _writes_miraheze(script_rel: str) -> bool:
    path = os.path.join(_ROOT, script_rel)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return bool(MIRAHEZE_TARGET_RE.search(fh.read()))
    except OSError:
        return False


def _steps(doc):
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict):
                yield step


def _offending_steps(path):
    """Steps that apply an edit to miraheze without the lockout `if:` guard."""
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        pytest.fail(f"{os.path.basename(path)} is not valid YAML: {e}")
    if not isinstance(doc, dict):
        return [], raw

    bad = []
    for step in _steps(doc):
        run = str(step.get("run") or "")
        if "--apply" not in run:
            continue
        if not any(_writes_miraheze(s) for s in SCRIPT_RE.findall(run)):
            continue
        if "lockout" not in str(step.get("if") or ""):
            bad.append(step.get("name") or run.strip().splitlines()[0][:60])
    return bad, raw


def _workflow_files():
    if not os.path.isdir(_WORKFLOWS):
        pytest.skip("no .github/workflows directory")
    return sorted(
        os.path.join(_WORKFLOWS, f)
        for f in os.listdir(_WORKFLOWS)
        if f.endswith((".yml", ".yaml"))
    )


def test_every_miraheze_writing_step_is_lockout_gated():
    failures = []
    for path in _workflow_files():
        bad, raw = _offending_steps(path)
        name = os.path.basename(path)
        if bad:
            failures.append(f"{name}: step(s) {bad} apply miraheze edits with no lockout `if:`")
        elif GUARD not in raw:
            # No offending step, but if the workflow applies miraheze edits at all
            # it should still define the guard the `if:` refers to.
            with open(path, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh.read())
            if isinstance(doc, dict):
                applies = any(
                    "--apply" in str(s.get("run") or "")
                    and any(_writes_miraheze(x) for x in SCRIPT_RE.findall(str(s.get("run") or "")))
                    for s in _steps(doc)
                )
                if applies:
                    failures.append(f"{name}: applies miraheze edits but never runs {GUARD}")
    assert not failures, "Unguarded miraheze writers:\n  " + "\n  ".join(failures)


def test_the_four_known_offenders_are_now_gated():
    """Named explicitly so a regression points at the right file immediately."""
    for name in ("dedupe-duplicate-qids.yml",
                 "sunset-jp-char-count-cats.yml",
                 "sunset-templates-not-transcluded-in-mainspace-cat.yml",
                 "tag-templates-not-transcluded-anywhere.yml"):
        path = os.path.join(_WORKFLOWS, name)
        assert os.path.isfile(path), f"{name} vanished; update this test deliberately"
        bad, raw = _offending_steps(path)
        assert not bad, f"{name} regressed: {bad}"
        assert GUARD in raw, f"{name} no longer runs {GUARD}"


def test_the_guard_helper_still_exists():
    """The `if:` conditions are worthless if the script they call is gone."""
    assert os.path.isfile(os.path.join(_ROOT, "shinto_miraheze", "wiki_edit_allowed.py"))


def test_wikidata_writers_are_not_dragged_into_this_rule():
    """Two wikis, two gates -- a Wikidata-only workflow needs the other one."""
    path = os.path.join(_WORKFLOWS, "create-items.yml")
    if not os.path.isfile(path):
        pytest.skip("create-items.yml not present")
    bad, raw = _offending_steps(path)
    assert not bad
    assert "wikidata_edit_allowed" in raw
