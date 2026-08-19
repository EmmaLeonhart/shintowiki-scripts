"""One place that decides how fast we may talk to Wikidata.

Pacing used to live as a per-call `time.sleep` in 100+ scripts, with values from 0.2s to 10s and a
number of call sites carrying none at all. Scattered constants are how a gap happens — nobody can
see the policy, so nobody notices a script that skips it.

`READ_INTERVAL` paces the API. `SPARQL_INTERVAL` paces the query service and is deliberately much
larger: this repo's floor for WDQS is 2.5s, set after an unpaced run fired ~365 queries and drew
repeated 503/504. Do not pace a SPARQL caller at READ_INTERVAL.
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
