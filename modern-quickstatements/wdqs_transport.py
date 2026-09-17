#!/usr/bin/env python3
"""
wdqs_transport.py
=================
One throttled, retrying WDQS transport, for the generators that were sharing a
copy-pasted one.

## Why this exists, and why it is deliberately small

**69 files** in this repo call WDQS and each hand-rolls its transport. On 2026-09-13
WDQS answered 200 and then cut a response short mid-row —

    json.decoder.JSONDecodeError: Unterminated string starting at:
    line 13162 column 9 (char 326356)

— which ended a forty-minute sweep at its last language with nothing written,
because these generators write their `.txt` only at the end.

⛔ **DO NOT PUT A NUMBER ON HOW MANY ARE FRAGILE.** Three separate regexes over this
population gave three wrong answers on 2026-09-13/14 — "65 of 72" missed every
`except Exception` and `except (ValueError, KeyError)`, which already catch a JSON
error; "50" counted a file fixed hours earlier whose clause puts the tuple in a
variable; "~41 with no retry loop" matched only `for attempt in range` and missed the
`for wait in (0, 15, 45, 135)` shape entirely. What is grounded, by reading: **34 have
some retry construct, 35 have none, and 10 already use the 15/45/135 backoff.**

**Migration is per-file reading and is NOT uniformly an upgrade.** Those 10 have a
stronger escalation than a flat one would give them, and no two of the unmigrated
transports share a body. Against the effort: the failure costs one day of one file,
because CI is `continue-on-error` and the next run repairs it. A hand-run is where it
hurts, and a hand-run is rare.

So this module covers **the three callers that were literally the same function
copy-pasted**, all written on 2026-09-12/13:

* `generate_invalid_p825_removals.py`
* `generate_ronsha_role_qualifiers.py`
* `generate_misplaced_form_removals.py`

Others adopt it when they are next touched — and as of 2026-09-16 that is all of
them but one. `generate_description_fixes.py` keeps its own, because it is imported
by its sibling and moving it is a separate change with its own blast radius.

⚠ This paragraph used to say that file "has the same policy". It does not, and this
module's own closing note is the evidence: its backoff is **30/60/90 over three
attempts**, the linear pattern lifted from it and then corrected here. Its 429 bail
and its retryable set do match; its escalation does not. Aligning it is that file's
own next change, not a docs edit — recorded in `queue.md` rather than done quietly
here.

## The policy, which is CLAUDE.md's and not this module's

* **`WDQS_THROTTLE = 2.5` between calls**, enforced HERE rather than at the call
  sites. Emma, 2026-08-24: *"You just want to rate limit within your scripts."*
  Pacing the transport is the only version a new caller cannot forget.
* **429 bails immediately, no retries.** Repo policy, unconditional.
* **503/504 and transport failures back off exponentially** — **15/45/135s over four
  attempts**, the pattern CLAUDE.md names as the floor and `generate_genbu_ids.py`
  implements. Four, not three: at three only 15 and 45 fire and the documented third
  step never happens. A truncated body is a transport failure, not a result.

  ⚠ This was 30/60/90 for its first day, copied from `generate_description_fixes.py`
  without checking it against the documented rule. Measured 2026-09-14: **10 of the 69
  WDQS callers already use 15/45/135**, so a migration onto the linear version would
  have quietly downgraded every one of them. The shared module has to carry the
  repo's pattern, not the pattern of whichever file it was lifted from.
"""

import csv
import http.client
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

ENDPOINT = "https://query-main.wikidata.org/sparql"
WDQS_THROTTLE = 2.5
# The default socket timeout. Per-caller, because the callers genuinely differ:
# 120s in fetch_shrines_tokiponize, 600s in site/generate_orphan_label_fixes.
TIMEOUT = 300
# FOUR attempts, because that is what makes the backoff 15/45/135. At three, only
# 15 and 45 ever fire and the documented third step is decoration — which is what
# this module shipped with for a day. `generate_genbu_ids.py`, the file CLAUDE.md
# points at as the floor, uses `for attempt in range(4)` for exactly this reason.
RETRIES = 4

# Everything that means "the transport failed", as opposed to "the server answered
# and the answer was no". A truncated body is in here because that is what actually
# happened; the rest are the neighbours it arrives with.
TRANSIENT = (json.JSONDecodeError, urllib.error.URLError, TimeoutError,
             ConnectionError, http.client.IncompleteRead)

# ⛔ CLIENT ERRORS THAT CANNOT SUCCEED ON RETRY. Observed 2026-09-15: a query with a
# 2,095-entry VALUES clause came back **414 URI Too Long** — this transport sends the
# query in the URL of a GET — and the loop dutifully backed off 15s, 45s and 135s
# before failing. Three minutes to re-learn a deterministic fact.
#
# The same reasoning that makes 429 bail applies here: the server has answered, and
# the answer will not change because we ask again. Only 5xx and transport failures are
# worth a second attempt.
#
# ⚠ 414 is also a real limitation of this module, not just a status to classify: it
# is GET-only, so a long VALUES clause does not fit. No current caller sends one —
# `report_stuck_katakana_readings.py` uses POST for exactly that reason. If a caller
# ever needs one, add POST rather than chunking around it here.
FATAL_STATUS = frozenset({400, 401, 403, 404, 405, 414, 431})

_last_call = 0.0


def _run(sparql_text, accept, parse, retries, endpoint, timeout, query_string):
    """The retry loop, shared by `query` and `query_csv`.

    ⛔ `parse` is applied INSIDE the `with`, and that placement is the point. A
    truncated body is what this module was built for, and for JSON it surfaces as a
    `JSONDecodeError` raised by the parse — so a version that read the bytes here
    and parsed them after the loop would put the very failure being retried outside
    the thing retrying it.
    """
    global _last_call
    req = urllib.request.Request(endpoint + "?" + query_string, headers={
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": accept,
    })
    for attempt in range(retries):
        gap = time.monotonic() - _last_call
        if gap < WDQS_THROTTLE:
            time.sleep(WDQS_THROTTLE - gap)
        _last_call = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return parse(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            if e.code in FATAL_STATUS:
                # Deterministic: retrying spends the whole backoff to fail identically.
                print(f"  WDQS {e.code} — not retryable, giving up", flush=True)
                raise
            if attempt == retries - 1:
                raise
            wait = 15 * (3 ** attempt)
            print(f"  WDQS {e.code} — retrying in {wait}s", flush=True)
            time.sleep(wait)
        except TRANSIENT as e:
            if attempt == retries - 1:
                raise
            wait = 15 * (3 ** attempt)
            print(f"  WDQS {type(e).__name__}: {e} — retrying in {wait}s", flush=True)
            time.sleep(wait)


def query(sparql_text, retries=RETRIES, endpoint=ENDPOINT, timeout=TIMEOUT):
    """Run a SPARQL query and return its `results.bindings`.

    Raises `SystemExit` on 429 without retrying, per repo policy. Retries a
    transport failure or a 5xx on the repo's 15/45/135s backoff, then re-raises.

    `timeout` exists because it was hardcoded at 300 and that is not universal:
    `site/generate_orphan_label_fixes.py` allowed **600**, and adopting the module
    without this parameter would have halved the budget of its longest query
    silently. Callers that were under 300 are left at their own figure rather than
    quietly given more.
    """
    return _run(sparql_text, "application/sparql-results+json",
                lambda r: json.load(r)["results"]["bindings"],
                retries, endpoint, timeout,
                "format=json&query=" + urllib.parse.quote(sparql_text))


def query_csv(sparql_text, retries=RETRIES, endpoint=ENDPOINT, timeout=TIMEOUT):
    """Run a SPARQL query asking for CSV, and return `list(csv.DictReader(...))`.

    ## Why a CSV mode exists at all, rather than moving those callers to `query`

    Seven callers ask WDQS for CSV, and two of them say why in their own docstring:
    *"CSV, not JSON: the JSON body for these result sets comes back truncated."*
    So converting them to `query` would reintroduce the exact failure this module
    was written to survive — on the result sets already known to provoke it. The
    CSV choice is load-bearing and is kept; what those callers were missing is the
    policy around it, which is all this adds.

    ⚠ **It is NOT as well protected as `query`, and the difference is real.** A
    truncated JSON body raises `JSONDecodeError` and is retried. A truncated CSV
    body is still valid CSV — it is simply shorter — so the only truncations
    catchable here are the ones the transport itself notices: `IncompleteRead`
    (a body short of its `Content-Length`), a dropped connection, a timeout. A
    server that closes cleanly mid-stream on a chunked response returns fewer rows
    and nothing raises. That was equally true of every hand-rolled version this
    replaces; it is stated here so nobody reads `query_csv` as making CSV safe.

    No caller passes a `format` parameter — the header does the asking, exactly as
    the seven hand-rolled versions did.
    """
    return _run(sparql_text, "text/csv",
                lambda r: list(csv.DictReader(io.StringIO(r.read().decode("utf-8")))),
                retries, endpoint, timeout,
                urllib.parse.urlencode({"query": sparql_text}))
