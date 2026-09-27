"""Every workflow passes actionlint (GitHub's own expression/syntax rules).

2026-09-27: `wikidata-drip.yml` used arithmetic inside `${{ }}` (`attempt + 1`). The YAML
parsed, every repo test passed, and GitHub rejected the file at startup, so the new drip
never ran. actionlint flags exactly that. Shellcheck is off; this is about the workflow
language, not shell style.

KNOWN holds workflows with pre-existing findings, recorded rather than fixed here: all
62 are one pattern, an array compared with a string, in the wiki-side workflows. A
workflow leaves KNOWN when it's fixed; new workflows must lint clean.
"""
import glob
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
KNOWN = {"wiki-cleanup.yml", "fandom-sync.yml", "git-synced-sync.yml"}

actionlint = shutil.which("actionlint")
pytestmark = pytest.mark.skipif(actionlint is None, reason="actionlint not installed")

FILES = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WF, "*.yml"))
               if os.path.basename(p) not in KNOWN)


@pytest.mark.parametrize("name", FILES)
def test_workflow_lints_clean(name):
    r = subprocess.run([actionlint, "-shellcheck=", "-pyflakes=", os.path.join(".github", "workflows", name)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
