"""A `shinto_miraheze` import must come AFTER the sys.path bootstrap that enables it.

This is an ordering bug, which is why nothing caught it: every file involved had
BOTH halves, just in the wrong order, so a grep for either one looked healthy.

How it happened, from the git history:

  2026-08-18  "Pace every Wikidata request site"  adds `from shinto_miraheze.wd_pace
              import wd_pace` near the top of ~23 files.
  2026-08-19  "Standardise the wiki agent"        adds the repo-root bootstrap and a
              `wikidata_user_agent` import — placing the bootstrap BELOW the pacing
              import added the day before.

From then on every one of those modules raised ModuleNotFoundError on line 1 of real
work, from any working directory.

What it cost, and why it stayed invisible for two days: `label-generator-regenerate.yml`
runs five of them on a schedule with `continue-on-error: true` on every step, so all
five died instantly and the workflow still reported **success**. The only visible trace
was the job time falling from ~12 minutes to ~55 seconds, and the commit diff shrinking
to a single date stamp in `docs/index.html` — which reads like "nothing to regenerate",
the most benign-looking outcome available.

The bootstrap walks UP from `__file__` looking for the `shinto_miraheze` package, so it
works from any cwd — but only if it has run yet.

2026-08-22: the same commit broke a SECOND way, and this test skipped it by design.
`_offenders()` read `if boot is None: continue` — a file with the import and no bootstrap
at all was waved through as "relies on being importable another way". For 69 files that
was not true. `python3 shinto_miraheze/foo.py` puts the SCRIPT's directory on sys.path[0],
never the repo root and never the cwd, so a package-absolute import from a file that is
not itself at the repo root cannot resolve without the bootstrap. 17 of the 69 were
invoked that way by a workflow and had been dying daily since 2026-08-19; the daily
`cleanup-loop` run had four red jobs, and the one that mattered most was silent —
`wikidata_edit_allowed.py`, the Wikidata lockout gate, is read as `exit 1 = LOCKED`, so
crashing on import gave the same answer as the real lockout it was reporting.

So the second test below removes the exemption: carry the bootstrap, or sit in a
directory that contains the package (only the repo root does).
"""
import ast
import io
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site"}
BOOTSTRAP = re.compile(r"while _uar != _uos\.path\.dirname\(_uar\)")


def _sources():
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _import_lines(path):
    """Line numbers of REAL shinto_miraheze imports, via ast — not a line regex.

    Several of these modules carry a usage example in their docstring:

        from shinto_miraheze.wikidata_edit_allowed import editing_allowed

    A regex over lines cannot tell that from code, and reported three files as
    importing before their own bootstrap when the "import" was prose.
    """
    src = io.open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and (node.module or "").split(".")[0] == "shinto_miraheze":
                out.append(node.lineno)
        elif isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "shinto_miraheze" for a in node.names):
                out.append(node.lineno)
    return sorted(out)


def _bootstrap_line(path):
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    return next((i + 1 for i, l in enumerate(lines) if BOOTSTRAP.search(l)), None)


def _offenders():
    out = []
    for path in _sources():
        boot = _bootstrap_line(path)
        if boot is None:
            continue                     # covered by the missing-bootstrap test below
        early = [n for n in _import_lines(path) if n < boot]
        if early:
            out.append("%s (bootstrap line %d, imports at %s)"
                       % (os.path.relpath(path, _ROOT).replace("\\", "/"), boot, early))
    return out


def test_bootstrap_precedes_every_shinto_miraheze_import():
    bad = _offenders()
    assert not bad, (
        "these import shinto_miraheze BEFORE the sys.path bootstrap that makes it "
        "importable, so they raise ModuleNotFoundError from any cwd: " + "; ".join(bad))


def _missing_bootstrap():
    out = []
    for path in _sources():
        if not _import_lines(path):
            continue
        if _bootstrap_line(path) is not None:
            continue
        # A file that sits BESIDE the package gets the repo root on sys.path[0] for
        # free, because sys.path[0] is the script's own directory. Nothing else does.
        if os.path.isdir(os.path.join(os.path.dirname(path), "shinto_miraheze")):
            continue
        out.append(os.path.relpath(path, _ROOT).replace("\\", "/"))
    return out


def test_every_shinto_miraheze_importer_carries_the_bootstrap():
    bad = _missing_bootstrap()
    assert not bad, (
        "these do a package-absolute shinto_miraheze import with no sys.path bootstrap "
        "and are not at the repo root, so `python <file>` raises ModuleNotFoundError: "
        + "; ".join(bad))


def test_the_walk_reaches_the_directories_this_bug_lived_in():
    """Guards against a vacuous pass — the same miscount shape as the endpoint
    migration, where a hand grep covered one directory and read as complete."""
    seen = {os.path.relpath(p, _ROOT).replace("\\", "/").split("/")[0]
            for p in _sources()}
    for d in ("modern-quickstatements", "shinto-label-generator", "site", "tests",
              "fandom", "recreate-deleted-wikidata"):
        assert d in seen, d
