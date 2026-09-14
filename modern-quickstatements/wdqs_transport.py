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

Others adopt it when they are next touched. `generate_description_fixes.py` keeps
its own — it has the same policy and is imported by its sibling, so moving it is a
separate change with its own blast radius.

## The policy, which is CLAUDE.md's and not this module's

* **`WDQS_THROTTLE = 2.5` between calls**, enforced HERE rather than at the call
  sites. Emma, 2026-08-24: *"You just want to rate limit within your scripts."*
  Pacing the transport is the only version a new caller cannot forget.
* **429 bails immediately, no retries.** Repo policy, unconditional.
* **503/504 and transport failures back off exponentially** — **15/45/135s**, which is
  the pattern CLAUDE.md names as the floor and `generate_genbu_ids.py` implements.
  A truncated body is a transport failure, not a result.

  ⚠ This was 30/60/90 for its first day, copied from `generate_description_fixes.py`
  without checking it against the documented rule. Measured 2026-09-14: **10 of the 69
  WDQS callers already use 15/45/135**, so a migration onto the linear version would
  have quietly downgraded every one of them. The shared module has to carry the
  repo's pattern, not the pattern of whichever file it was lifted from.
"""

import http.client
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
RETRIES = 3

# Everything that means "the transport failed", as opposed to "the server answered
# and the answer was no". A truncated body is in here because that is what actually
# happened; the rest are the neighbours it arrives with.
TRANSIENT = (json.JSONDecodeError, urllib.error.URLError, TimeoutError,
             ConnectionError, http.client.IncompleteRead)

_last_call = 0.0


def query(sparql_text, retries=RETRIES, endpoint=ENDPOINT):
    """Run a SPARQL query and return its `results.bindings`.

    Raises `SystemExit` on 429 without retrying, per repo policy. Retries a
    transport failure or a 5xx on the repo's 15/45/135s backoff, then re-raises.
    """
    global _last_call
    url = endpoint + "?format=json&query=" + urllib.parse.quote(sparql_text)
    req = urllib.request.Request(url, headers={
        "User-Agent": WIKIDATA_USER_AGENT,
        "Accept": "application/sparql-results+json",
    })
    for attempt in range(retries):
        gap = time.monotonic() - _last_call
        if gap < WDQS_THROTTLE:
            time.sleep(WDQS_THROTTLE - gap)
        _last_call = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit("429 from WDQS — bailing.")
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
