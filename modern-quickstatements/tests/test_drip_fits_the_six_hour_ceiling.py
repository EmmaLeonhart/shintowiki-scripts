"""500 edits a day have to fit in six hours, because six hours is a hard ceiling.

GitHub kills a hosted job at 6h of execution whatever `timeout-minutes` says.
`direct-daily-edits.yml` carried `timeout-minutes: 540` through September to make
room for the 300 -> 500 cap raise, and it never took effect: measured 2026-09-10,
six of the last eight runs ended at exactly 6h00m ±30s with conclusion `cancelled`,
the most recent at edit 356 of 501. Roughly 145 lines were dropped every run while
the declared timeout sat three hours out of reach.

Nothing caught it because a killed run still makes every edit it got through, and
`cancelled` reads like something external rather than like a limit.

So two things are pinned here: no declared timeout may exceed the ceiling, and the
cap times the mean delay must fit inside it.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
ROOT = os.path.dirname(MQ)
if MQ not in sys.path:
    sys.path.insert(0, MQ)

import direct_daily_edits as dde  # noqa: E402

# GitHub's documented maximum execution time for a job on a hosted runner.
GITHUB_JOB_CEILING_MIN = 360

WORKFLOWS = os.path.join(ROOT, ".github", "workflows")


def _declared_timeouts(path):
    """[(lineno, minutes)] for every literal `timeout-minutes:` in a workflow.

    Literal only: an expression (`${{ … }}`) cannot be read statically, and the one
    that mattered here WAS an expression — which is part of why 540 was invisible.
    Those are caught by the separate test below.
    """
    out = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        m = re.match(r"\s*timeout-minutes:\s*(\d+)\s*$", line)
        if m:
            out.append((n, int(m.group(1))))
    return out


@pytest.mark.parametrize("name", sorted(
    f for f in os.listdir(WORKFLOWS) if f.endswith((".yml", ".yaml"))))
def test_no_declared_timeout_exceeds_the_ceiling(name):
    bad = [(n, m) for n, m in _declared_timeouts(os.path.join(WORKFLOWS, name))
           if m > GITHUB_JOB_CEILING_MIN]
    assert not bad, (
        f"{name} declares a timeout above GitHub's {GITHUB_JOB_CEILING_MIN}-minute "
        f"hosted-job ceiling, which cannot take effect: {bad}")


def test_the_drip_declares_a_literal_timeout_under_the_ceiling():
    """An expression here is what hid 540; the value must be readable at rest."""
    path = os.path.join(WORKFLOWS, "direct-daily-edits.yml")
    text = open(path, encoding="utf-8").read()
    assert "needs.timeout-window" not in text, (
        "the timeout-window job is back — it existed only to supply 540, a number "
        "above the ceiling")
    timeouts = _declared_timeouts(path)
    assert timeouts, "the edit job must declare a literal timeout-minutes"
    assert all(m <= GITHUB_JOB_CEILING_MIN for _, m in timeouts), timeouts


def test_the_cap_fits_the_ceiling_at_the_mean_delay():
    """MAX_EDITS x mean delay must leave real headroom inside 6h.

    This is the arithmetic that was wrong: at [30, 90]s the mean is 60s and 500
    edits need 8.3h. The assertion is on the MEAN rather than the worst case
    because 500 independent draws do not average their maximum — but it demands
    45 minutes of headroom so a slow run is not immediately at the edge.
    """
    mean_delay = (dde.MIN_DELAY + dde.MAX_DELAY) / 2
    hours = dde._DEFAULT_MAX_EDITS * mean_delay / 3600
    assert hours <= (GITHUB_JOB_CEILING_MIN - 45) / 60, (
        f"{dde._DEFAULT_MAX_EDITS} edits at a {mean_delay}s mean delay is {hours:.1f}h, "
        f"which does not fit the {GITHUB_JOB_CEILING_MIN / 60:.0f}h ceiling with headroom")


def test_the_delay_stays_inside_bot_norms():
    """The fix was to shorten the delay, so pin that it did not become a hammer.

    CLAUDE.md's wiki-side THROTTLE targets ~24 edits/min; this path must stay far
    under that. It is also a floor, not just a ceiling: a delay of a couple of
    seconds would fit the window and be exactly the 'do not hammer' failure.
    """
    assert dde.MIN_DELAY >= 15, "too fast — this is a bot on someone else's servers"
    assert dde.MAX_DELAY > dde.MIN_DELAY
    mean_delay = (dde.MIN_DELAY + dde.MAX_DELAY) / 2
    assert 60 / mean_delay <= 4, "more than 4 edits/min is not this project's pace"
