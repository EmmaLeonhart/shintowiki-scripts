"""One place that decides how fast we may talk to Wikidata.

Emma asked on 2026-08-04 whether the scripts rate-limit Wikidata at all, and the honest answer,
measured on 2026-08-18, was "mostly": 108 call sites carried their own `time.sleep`, with values
scattered from 0.2s to 10s, and a handful had nothing. Scattered per-call constants are how the
handful happens — nobody can see the policy, so nobody notices a script that skips it.

So the policy lives here, and the reason it matters is not politeness: the standing concern is
Wikidata **scrutiny** (Emma, 2026-07-30 — "20% chance… operational security issue"), and scrutiny
follows a visible pattern rather than raw volume. A steady, paced reader looks like every other
tool; an unpaced loop is the thing that stands out in a log.

`READ_INTERVAL` is the interval between successive read requests from one process. 0.3s matches what
the majority of existing call sites already used, and is well inside what the API tolerates for
authenticated reads — this is about looking ordinary, not about staying under a limit.
"""
import time

READ_INTERVAL = 0.3
# SPARQL is not the API. This repo's own rule (CLAUDE.md, after match_jinjacho_shrines.py fired
# ~365 queries in a run and drew repeated 503/504): WDQS_THROTTLE = 2.5 is the FLOOR for the query
# service. Do not pace a SPARQL caller at READ_INTERVAL.
SPARQL_INTERVAL = 2.5

_last = 0.0


def wd_pace(interval: float = READ_INTERVAL) -> None:
    """Block until at least `interval` seconds have passed since the previous call.

    Sleeps the REMAINDER rather than a flat interval, so a call site that already spent time doing
    work is not slowed twice. Process-local by design: the scripts run one at a time under Actions,
    and a cross-process limiter would be a lie about what it can enforce.
    """
    global _last
    now = time.monotonic()
    wait = interval - (now - _last)
    if wait > 0:
        time.sleep(wait)
        now = time.monotonic()
    _last = now
