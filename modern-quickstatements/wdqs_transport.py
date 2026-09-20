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

Others adopt it when they are next touched. **Adopters: 63.** Of the 26 hand-rolled
transports left, **18 are clean on all four properties** — a retry loop, a 429 that
bails, a truncated body that is retried, and pacing at or above 2.5s — audited with
`ast` on 2026-09-16. There is no named defect left in the remainder, so there is
nothing here to batch; each rides its own file's next real change.

⛔ **Migration is not uniformly an upgrade, and three mechanisms prove it** — this is
a specific claim, not a general caution:

1. **A stronger hand-rolled backoff.** `generate_modern_shrine_ranking_qualifiers`
   escalates to 450s against this module's 195s, so it STAYS as it is.
2. **`strict=False` parsing**, which a caller may need and the shared path does not
   impose.
3. **A caller pacing itself above the floor.**

`query()` therefore takes `timeout` and `throttle` for the last two, and
`max(throttle, WDQS_THROTTLE)` means no caller can ask to be FASTER than the floor —
the parameter can only slow a caller down.

`generate_description_fixes.py` stays off this module on purpose: its sibling imports
from it, so moving it is a separate change with its own blast radius. It carries the
policy rather than sharing it.

⚠ This paragraph used to say its escalation diverged — **30/60/90 over three
attempts**, the linear pattern this module was lifted from. That was true when
written and was fixed in that file on **2026-09-16**: `RETRIES = 4`,
`wait = 15 * (3 ** attempt)`, `WDQS_THROTTLE = 2.5`, and a 429 that bails from
`except HTTPError`. It now matches on all four properties. The paragraph also said
the divergence was "recorded in `queue.md`"; it is not, and should not be — the
thing it described is done.

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

# The 15/45/135 backoff itself, as a function, so the hand-rolled transports can
# import it instead of each spelling it out.
#
# ⛔ They did not spell it out. Measured 2026-09-20 across every WDQS caller in the
# repo: EIGHT hand-rolled ones slept `10 * attempt` — 10s then 20s — which is the
# sequence that cost the en-label workflow five days:
#
#     SPARQL 502 transient (attempt 1/3)
#     FATAL: 429 Too Many Requests from SPARQL endpoint — bailing
#
# CLAUDE.md says the opposite twice: *"503/504 → back off hard, do not retry
# tightly"*, and the floor it points at in `generate_genbu_ids.py` comes *"with
# exponential backoff (15/45/135s)"*.
#
# ⚠ Two of those eight — `generate_kana_qualifier_remove` and
# `generate_katakana_reading_remove` — already carried `15 * (3 ** (attempt - 1))`
# in their 503/504 branch, with the CLAUDE.md line quoted above it, while their
# truncated-body and timeout branches still slept 10s. So the rule was known, and
# applied to the branch someone was looking at. That is the argument for one
# importable definition rather than a number retyped per branch.
BACKOFF_BASE = 15
BACKOFF_FACTOR = 3


def backoff(attempt):
    """Seconds to wait before retry `attempt`, 1-based: 15, 45, 135.

    1-based because every hand-rolled loop in this repo counts
    `for attempt in range(1, retries + 1)` and guards its sleep with
    `if attempt < retries`, so the fourth attempt never sleeps.
    """
    return BACKOFF_BASE * (BACKOFF_FACTOR ** (attempt - 1))


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
# ⚠ 414 was also a real limitation of this module: it was GET-only, so a long VALUES
# clause did not fit, and the note here said *"if a caller ever needs one, add POST
# rather than chunking around it here."* Callers needed one — every WDQS caller
# pacing below the 2.5s floor turned out to be a POST caller — so `post=True` exists
# now and this status stays classified rather than worked around.
FATAL_STATUS = frozenset({400, 401, 403, 404, 405, 414, 431})

_last_call = 0.0


def _parse_bindings(r):
    """Decode a WDQS JSON body to `results.bindings`, tolerantly.

    ⛔ `strict=False` is load-bearing, not tidiness. Python's JSON parser rejects a
    RAW control character inside a string literal, and WDQS emits them: a label or
    description containing a real newline comes back unescaped. Five callers in this
    repo already parse with `strict=False` for exactly that reason, one of them
    saying so in a comment — *"strict=False because literals legitimately contain
    raw newlines."*

    This module did not, and the consequence was worse than a plain failure: a
    `JSONDecodeError` is in `TRANSIENT`, so a response that was perfectly readable
    would be RETRIED — 15s, 45s, 135s — and then re-raised. Three minutes and
    change to fail on data we could have parsed, which is the same shape as the 414
    note above.

    It also meant migrating any of those five onto this module would have been a
    DOWNGRADE. That is the concrete version of the queue item's "migration is not
    uniformly an upgrade", which until now named only backoff strength.

    A truncated body still raises here and is still retried, which is the behaviour
    this module was built for: `strict=False` forgives control characters, not a
    body that stops mid-token.
    """
    return json.loads(r.read().decode("utf-8"), strict=False)["results"]["bindings"]


def _run(sparql_text, accept, parse, retries, endpoint, timeout, query_string, post,
         throttle):
    """The retry loop, shared by `query` and `query_csv`.

    ⛔ `parse` is applied INSIDE the `with`, and that placement is the point. A
    truncated body is what this module was built for, and for JSON it surfaces as a
    `JSONDecodeError` raised by the parse — so a version that read the bytes here
    and parsed them after the loop would put the very failure being retried outside
    the thing retrying it.
    """
    global _last_call
    headers = {"User-Agent": WIKIDATA_USER_AGENT, "Accept": accept}
    if post:
        # The SAME encoded string, in the body instead of the URL — which is the
        # whole point of POST here: a long VALUES clause does not fit in a GET URL
        # and comes back 414, deterministically, after burning the full backoff.
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(endpoint, data=query_string.encode("utf-8"),
                                     headers=headers)
    else:
        req = urllib.request.Request(endpoint + "?" + query_string, headers=headers)
    # ⛔ The floor is a FLOOR. A caller may ask to be SLOWER than 2.5s and four do
    # — they chose 3s for themselves — but `max` means none can ask to be faster,
    # whatever it passes. Migrating a 3s caller onto a bare 2.5s would have made it
    # less polite than its author chose, on the axis CLAUDE.md cares most about.
    pace = max(throttle if throttle is not None else WDQS_THROTTLE, WDQS_THROTTLE)
    for attempt in range(retries):
        gap = time.monotonic() - _last_call
        if gap < pace:
            time.sleep(pace - gap)
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
            wait = backoff(attempt + 1)
            print(f"  WDQS {e.code} — retrying in {wait}s", flush=True)
            time.sleep(wait)
        except TRANSIENT as e:
            if attempt == retries - 1:
                raise
            wait = backoff(attempt + 1)
            print(f"  WDQS {type(e).__name__}: {e} — retrying in {wait}s", flush=True)
            time.sleep(wait)


def query(sparql_text, retries=RETRIES, endpoint=ENDPOINT, timeout=TIMEOUT, post=False,
          throttle=None):
    """Run a SPARQL query and return its `results.bindings`.

    Raises `SystemExit` on 429 without retrying, per repo policy. Retries a
    transport failure or a 5xx on the repo's 15/45/135s backoff, then re-raises.

    `throttle` lets a caller be SLOWER than the 2.5s floor, never faster. Four
    callers pace themselves at 3s by their own choice, and moving them onto a bare
    2.5s would have quietly made them less polite than their authors decided.

    `timeout` exists because it was hardcoded at 300 and that is not universal:
    `site/generate_orphan_label_fixes.py` allowed **600**, and adopting the module
    without this parameter would have halved the budget of its longest query
    silently. Callers that were under 300 are left at their own figure rather than
    quietly given more.
    """
    return _run(sparql_text, "application/sparql-results+json",
                _parse_bindings,
                retries, endpoint, timeout,
                "format=json&query=" + urllib.parse.quote(sparql_text), post,
                throttle)


def query_csv(sparql_text, retries=RETRIES, endpoint=ENDPOINT, timeout=TIMEOUT, post=False,
              throttle=None):
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
                urllib.parse.urlencode({"query": sparql_text}), post,
                throttle)
