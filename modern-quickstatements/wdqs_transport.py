#!/usr/bin/env python3
"""
wdqs_transport.py
=================
One throttled, retrying WDQS transport, for the generators that were sharing a
copy-pasted one.

## Why this exists, and why it is deliberately small

Seventy-two files in this repo call WDQS and each hand-rolls its transport. On
2026-09-13 WDQS answered 200 and then cut a response short mid-row —

    json.decoder.JSONDecodeError: Unterminated string starting at:
    line 13162 column 9 (char 326356)

— which ended a forty-minute sweep at its last language with nothing written,
because these generators write their `.txt` only at the end. A survey the same
evening found **65 of the 72 cannot survive that**.

Sixty-five files is not a change to make in one sitting, and the severity does not
call for it: every generator runs `continue-on-error` in CI and the next day's run
repairs the file, which is the pacing this project wants. A hand-run is where it
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
* **503/504 and transport failures back off hard** — 30/60/90s — and then give up.
  A truncated body is a transport failure, not a result.
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
    transport failure or a 5xx on a 30/60/90s backoff, then re-raises.
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
            wait = 30 * (attempt + 1)
            print(f"  WDQS {e.code} — retrying in {wait}s", flush=True)
            time.sleep(wait)
        except TRANSIENT as e:
            if attempt == retries - 1:
                raise
            wait = 30 * (attempt + 1)
            print(f"  WDQS {type(e).__name__}: {e} — retrying in {wait}s", flush=True)
            time.sleep(wait)
