"""The shared WDQS transport: throttled, 429 bails, transport failures retry.

Written 2026-09-13 after a truncated body ended a forty-minute sweep. A survey the
same evening found 65 of the 72 WDQS callers in this repo cannot survive that —
each hand-rolls its own transport. Sixty-five files is not a change to make in one
sitting and the severity does not call for it: CI runs every generator
`continue-on-error` and the next day repairs the file.

So this module took the three callers that were literally the same function
copy-pasted, all written 2026-09-12/13. What is pinned here is the policy, because
the policy is CLAUDE.md's and not the module's: 429 bails unconditionally, a
transport failure backs off, and the throttle lives in the transport where a new
caller cannot forget it.
"""

import importlib.util
import os
import sys
import time
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _restore_the_globals_these_tests_patch():
    """⛔ `_mod()` gives a FRESH module object, but `mod.time` and `mod.urllib` are
    the same singletons every other test imports. So `mod.time.sleep = ...` below
    is not a local patch — it clobbers `time.sleep` process-wide and, without this,
    leaves it clobbered.

    It left `tests/test_wikidata_pacing.py::test_wd_pace_actually_waits` failing
    for anyone who ran the suite with this directory ahead of `tests/`: wd_pace
    called a no-op sleep and returned instantly. CI only stayed green because
    `ci.yml` happens to list `tests/` first, which is argument order, not
    isolation — the next person to reorder that line would have inherited a
    failure with nothing in it pointing here.
    """
    sleep, urlopen = time.sleep, urllib.request.urlopen
    try:
        yield
    finally:
        time.sleep, urllib.request.urlopen = sleep, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

MIGRATED = ("generate_invalid_p825_removals.py",
            "generate_ronsha_role_qualifiers.py",
            "generate_misplaced_form_removals.py",
            # Adopted 2026-09-15, on the tick after its reference fix — the
            # "rides with the file's next real change" cadence the queue item
            # sets. It qualified on the item's own test for whether a migration
            # is an upgrade: its transport spaced queries **0.5s** apart (the
            # exact figure CLAUDE.md cites from the match_jinjacho_shrines.py
            # incident that produced the 2.5s floor) and backed off 5/10/15,
            # weaker than the documented 15/45/135. Safe on the module's
            # GET-only constraint: three short fixed queries, no VALUES clause.
            "generate_court_rank_quickstatements.py",
            # Adopted 2026-09-15 alongside its own reference fix, same cadence.
            # Its WDQS client was the weakest in the set: no retry at all, no
            # throttle, and a `if r.status == 429` check after a SUCCESSFUL
            # urlopen — dead code, because urllib raises HTTPError on a 429 and
            # never returns a response to test. So the whole documented policy
            # (bail on 429, back off on 5xx and truncation, 2.5s spacing) was
            # absent, and the module is strictly stronger.
            #
            # ⚠ It also talks to ja.wikipedia, which the other adopters do
            # through `requests`. Its fetcher moved to `requests` too rather
            # than narrowing the urlopen assertion below — the assertion is the
            # evidence, and an adopter with a raw urlopen in it cannot be told
            # apart from one that regrew a WDQS client.
            "generate_saijin_quickstatements.py",
            # Adopted 2026-09-15 with its own skip-set fix, same cadence and the
            # same client as its saijin sibling: no retry, no throttle, and a
            # `if r.status == 429` after a successful urlopen that can never fire.
            "generate_honzon_quickstatements.py",
            # ── Adopted 2026-09-16, as one batch, and the batching needs a word ──
            # The queue item says migration "rides with each file's next real
            # change", because it is per-file reading and NOT uniformly an upgrade.
            # That still holds. What the reading found is a SUBCLASS where it is
            # uniform: a file whose only 429 handling is `if r.status == 429` after
            # a successful urlopen. That branch is unreachable — urllib raises
            # HTTPError on a 429 and never returns a response to test (proved
            # against a local server that answers 429: the with-body never runs) —
            # and none of these five had any retry construct at all. So the whole
            # documented policy was absent from every one of them, and the module
            # is strictly stronger. No judgement call was left per file.
            #
            # These five are the members of that subclass whose ONLY urlopen was
            # the WDQS one, so nothing else had to move to satisfy the assertion
            # below. The rest of the subclass also fetches ja.wikipedia or the
            # Wikidata API through urlopen; converting those fetchers is each
            # file's own change, on the cadence above.
            "generate_bunrei_qualifier_repair.py",
            "generate_reisai_qualifier_repair.py",
            # ⚠ This one paced itself with a bare `wd_pace()` — READ_INTERVAL,
            # **0.3s** — for a SPARQL caller, which `wd_pace.py` tells you in its
            # own docstring not to do, and it fires one query per property pair.
            # 0.5s in generate_court_rank_quickstatements.py was called out as the
            # figure from the incident that set the 2.5s floor; this was lower.
            "generate_kami_parent_qualifiers.py",
            "generate_sango_quickstatements.py",
            "generate_shinto_honorifics.py")


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_t_wdqs", os.path.join(MQ, "wdqs_transport.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    status = 200

    def __init__(self, body):
        self._body = body

    def read(self, *a):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


OK = b'{"results": {"bindings": [{"x": {"value": "ok"}}]}}'
SHORT = b'{"results": {"bindings": [{"x": {"value": "tru'


def test_a_truncated_body_is_retried():
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        return _Resp(SHORT if calls["n"] == 1 else OK)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    assert mod.query("SELECT * WHERE {}") == [{"x": {"value": "ok"}}]
    assert calls["n"] == 2, f"not retried ({calls['n']} call(s))"


def test_429_bails_without_retrying():
    """Unconditional repo policy. Widening the retry set must not sweep it up."""
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except SystemExit as e:
        assert "429" in str(e)
    else:
        raise AssertionError("429 did not bail")
    assert calls["n"] == 1, f"429 retried {calls['n']} times"


def test_a_5xx_is_retried_then_gives_up():
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    else:
        raise AssertionError("a persistent 504 should surface, not be swallowed")
    assert calls["n"] == mod.RETRIES


def test_the_throttle_is_in_the_transport():
    """Emma, 2026-08-24: "You just want to rate limit within your scripts." Pacing
    the transport is the only version a new caller cannot forget."""
    mod = _mod()
    assert mod.WDQS_THROTTLE >= 2.5, (
        "the documented floor is 2.5s; a lower one is how this repo 429'd itself "
        "out of every weekly refresh for a month")
    src = open(os.path.join(MQ, "wdqs_transport.py"), encoding="utf-8").read()
    assert "_last_call" in src and "time.monotonic()" in src, (
        "the throttle is no longer enforced inside query()")


def test_a_429_check_after_a_successful_urlopen_can_never_fire():
    """The mechanism that made the 2026-09-16 batch a uniform upgrade rather than a
    judgement call — pinned because it is the whole argument.

    Eleven WDQS callers in this repo carried, or carried until that batch::

        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status == 429:
                raise SystemExit("429 from WDQS — bailing.")

    which reads as the repo's unconditional 429 policy and is not it. urllib's
    default opener raises `HTTPError` for any non-2xx, so the body of that `with`
    never runs on a 429 and `r.status` is always a success code. The policy held in
    those files only by accident, through an uncaught traceback.

    Asserted against a real server rather than from memory, because "urlopen raises
    on 4xx" is exactly the kind of thing that gets asserted confidently and wrongly.
    """
    import http.server
    import threading
    import urllib.error

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(429)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        reached = False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/", timeout=10) as r:
                reached = r.status
        except urllib.error.HTTPError as e:
            assert e.code == 429
        assert reached is False, (
            "urlopen returned a 429 response instead of raising, so `if r.status == 429` "
            "would be live after all — re-read the migration note in MIGRATED above")
    finally:
        srv.shutdown()


def test_the_copy_pasted_transports_are_gone():
    """These three carried the same function with no retry at all. If one grows its
    own urlopen back, it has left the shared policy behind."""
    for name in MIGRATED:
        src = open(os.path.join(MQ, name), encoding="utf-8").read()
        assert "import wdqs_transport" in src, f"{name} no longer uses the transport"
        assert "urllib.request.urlopen" not in src, (
            f"{name} calls urlopen directly again, outside the retry policy")


def test_the_backoff_is_the_repo_pattern_not_the_one_it_was_lifted_from():
    """15/45/135, exponential — CLAUDE.md names it the floor and
    `generate_genbu_ids.py` implements it as `time.sleep(15 * (3 ** attempt))`.

    ⚠ This module shipped with 30/60/90 for its first day, copied from
    `generate_description_fixes.py` without checking it against the rule. Measured
    2026-09-14: **10 of the 69 WDQS callers already use 15/45/135**, so migrating any
    of them onto the linear version would have quietly downgraded it. A shared module
    has to carry the repo's pattern, not the pattern of whichever file it came from.
    """
    mod = _mod()
    waits = []
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda s: waits.append(s)
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    # The last attempt re-raises rather than sleeping, so RETRIES-1 waits. All three
    # documented steps must actually fire: at RETRIES=3 the 135 never happens, which
    # is what this module shipped with for a day.
    assert waits == [15, 45, 135], waits
    assert mod.RETRIES == 4, (
        "four attempts is what makes the backoff 15/45/135; generate_genbu_ids.py, "
        "the file CLAUDE.md points at as the floor, uses range(4)")


def test_a_deterministic_client_error_is_not_retried():
    """⛔ Observed 2026-09-15: a query with a 2,095-entry VALUES clause came back
    414 URI Too Long — this transport sends the query in the URL of a GET — and the
    loop backed off 15s, 45s and 135s before failing. Three minutes to re-learn a
    deterministic fact.

    The reasoning that makes 429 bail applies: the server has answered, and the
    answer does not change because we ask again. Only 5xx and transport failures are
    worth a second attempt.
    """
    mod = _mod()
    for code in (400, 403, 404, 414, 431):
        calls = {"n": 0}

        def fake(req, timeout=None, _c=code):
            calls["n"] += 1
            raise mod.urllib.error.HTTPError(req.full_url, _c, "no", {}, None)

        mod.urllib.request.urlopen = fake
        mod.time.sleep = lambda *_: None
        mod.WDQS_THROTTLE = 0
        try:
            mod.query("SELECT * WHERE {}")
        except mod.urllib.error.HTTPError:
            pass
        else:
            raise AssertionError(f"{code} should surface")
        assert calls["n"] == 1, f"{code} was retried {calls['n']} times"


def test_a_5xx_is_still_retried_after_that_change():
    """The narrowing must not have swept up the errors that ARE worth retrying."""
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    assert calls["n"] == mod.RETRIES, f"503 attempted {calls['n']} times"
