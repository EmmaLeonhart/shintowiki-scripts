"""Every script that talks to Wikidata must pace itself. This is the test that keeps it true.

Emma asked on 2026-08-04 whether the scripts rate-limit Wikidata at all. The answer on 2026-08-18
was "108 call sites do, four didn't" — and the four were only found by grepping, two weeks after she
asked. The fix is not the four files; it is that nothing was checking.

Why it is worth a test rather than a note: the standing risk is Wikidata **scrutiny** (her 07-30
estimate, 20% chance of a block being "a relatively significant step back"), and an unpaced loop is
exactly the shape that stands out in someone else's log. This is the same failure mode as the User-
Agent sprawl — a policy that lives as a convention in 100+ files drifts silently until something
notices from the outside.

A file passes if it either calls `wd_pace()` (the shared limiter) or carries its own `time.sleep`.
Existing per-call sleeps are grandfathered deliberately: the point is that a request loop is paced,
not that every script is converted.
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site", "tests"}
# An HTTP call, not `dict.get`. The first cut of this test matched `.get(` and flagged two dozen
# files that merely build a wikidata.org LINK STRING for a report — a test that cries wolf gets
# deleted, so it is narrowed to call forms that actually issue a request.
REQUEST = re.compile(
    r"requests\.(get|post)\(|(?:s|ss|sess|session|http|client)\.(?:get|post)\(|"
    r"urlopen\(|mwclient\.Site\(")
# And the file must name a wikidata ENDPOINT, not just a wiki page URL.
WIKIDATA = re.compile(r"wikidata\.org/w/api|query\.wikidata\.org|wikidata\.org/sparql|"
                      r"quickstatements[^/]*\.(?:org|toolforge)", re.I)
PACED = re.compile(r"wd_pace\(|time\.sleep\(|RATE_LIMIT|rate_limit|--sleep")


def _py_files():
    for dp, dn, fn in os.walk(_ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.endswith(".py"):
                yield os.path.join(dp, f)


def test_every_wikidata_requester_paces_itself():
    offenders = []
    for p in _py_files():
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if not WIKIDATA.search(t) or not REQUEST.search(t):
            continue
        if PACED.search(t):
            continue
        offenders.append(os.path.relpath(p, _ROOT).replace("\\", "/"))
    assert not offenders, (
        "these scripts issue Wikidata requests with no pacing at all — add wd_pace() from "
        "shinto_miraheze.wd_pace to the request loop:\n  " + "\n  ".join(sorted(offenders))
    )


def test_wd_pace_actually_waits():
    import time
    from shinto_miraheze.wd_pace import wd_pace

    wd_pace(0.05)
    t0 = time.monotonic()
    wd_pace(0.05)
    assert time.monotonic() - t0 >= 0.04, "wd_pace did not wait between successive calls"


def test_wd_pace_does_not_double_charge_slow_callers():
    """A caller that already spent longer than the interval should not be slowed again."""
    import time
    from shinto_miraheze.wd_pace import wd_pace

    wd_pace(0.05)
    time.sleep(0.06)
    t0 = time.monotonic()
    wd_pace(0.05)
    assert time.monotonic() - t0 < 0.02, "wd_pace slept even though the interval had already elapsed"
