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
"""
import io
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site", "tests"}
BOOTSTRAP = re.compile(r"while _uar != _uos\.path\.dirname\(_uar\)")
IMPORT = re.compile(r"^\s*(?:from|import)\s+shinto_miraheze\b")


def _sources():
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _offenders():
    out = []
    for path in _sources():
        lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
        boot = next((i for i, l in enumerate(lines) if BOOTSTRAP.search(l)), None)
        if boot is None:
            continue                     # relies on being importable another way
        early = [i + 1 for i, l in enumerate(lines) if IMPORT.match(l) and i < boot]
        if early:
            out.append("%s (bootstrap line %d, imports at %s)"
                       % (os.path.relpath(path, _ROOT).replace("\\", "/"),
                          boot + 1, early))
    return out


def test_bootstrap_precedes_every_shinto_miraheze_import():
    bad = _offenders()
    assert not bad, (
        "these import shinto_miraheze BEFORE the sys.path bootstrap that makes it "
        "importable, so they raise ModuleNotFoundError from any cwd: " + "; ".join(bad))


def test_the_walk_reaches_the_directories_this_bug_lived_in():
    """Guards against a vacuous pass — the same miscount shape as the endpoint
    migration, where a hand grep covered one directory and read as complete."""
    seen = {os.path.relpath(p, _ROOT).replace("\\", "/").split("/")[0]
            for p in _sources()}
    for d in ("modern-quickstatements", "shinto-label-generator", "site"):
        assert d in seen, d
