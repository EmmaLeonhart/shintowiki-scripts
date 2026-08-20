"""No script may still request the retired `query.wikidata.org` endpoint.

The old endpoint threw repeated 503/504 during the 2026-08-03 rematch's
17,549-candidate P131 pass, which is why the tree moved to
`query-main.wikidata.org`. The migration ran in two halves — 15 files in
`modern-quickstatements/` on 2026-08-04, the remaining 21 on 2026-08-20 — and
between them the queue recorded the rest as blocked on two things that had both
stopped being true: `mwclient` (installed, 0.11.0) and the Miraheze blackout
(ended 2026-08-19), neither of which a Wikidata endpoint change ever depended on.

Why this is a test and not a one-off grep: the queue's own count was 9, taken
from `shinto_miraheze/` alone. There were 21, and the other 12 sit in
`shinto-label-generator/`, five of them run on a CI schedule with
`continue-on-error: true` — so an endpoint 503 there fails the step silently and
the workflow still goes green. A hand count missed a whole directory once; this
makes the next one impossible.
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site", "tests"}
RETIRED = re.compile(r"https://query\.wikidata\.org/sparql")


def _sources():
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def test_no_script_targets_the_retired_endpoint():
    offenders = []
    for path in _sources():
        with open(path, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if RETIRED.search(line):
                    offenders.append("%s:%d" % (os.path.relpath(path, _ROOT), n))
    assert not offenders, (
        "these still request the retired query.wikidata.org endpoint: "
        + ", ".join(offenders))


def test_the_test_can_actually_see_both_migrated_directories():
    """A walk that silently covered nothing would pass vacuously — the exact
    shape of the miscount this test exists to prevent."""
    seen = {os.path.relpath(p, _ROOT).replace("\\", "/").split("/")[0]
            for p in _sources()}
    assert "shinto_miraheze" in seen
    assert "shinto-label-generator" in seen
