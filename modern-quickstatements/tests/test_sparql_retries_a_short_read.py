"""A truncated WDQS body must be retried, not allowed to end the run.

`generate_description_fixes.sparql` is the single transport for that script and for
`generate_description_adds.py`. Its retry loop caught `HTTPError` only.

On 2026-09-13 WDQS answered 200 and then cut the response short mid-row:

    json.decoder.JSONDecodeError: Unterminated string starting at:
    line 13162 column 9 (char 326356)

That is not an `HTTPError`, so it escaped the loop and killed a 40-minute sweep at
the last language with nothing written — these generators only write their `.txt`
at the very end, so one short read costs the whole run. It is also the kind of
failure that then gets reported as "bailed (usually HTTP 429 from WDQS)".

429 still bails immediately and without retries, per CLAUDE.md. What changed is
that everything else meaning "the transport failed" backs off and tries again.
"""

import importlib.util
import inspect
import json
import os
import sys
import time
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)


@pytest.fixture(autouse=True)
def _restore_the_globals_these_tests_patch():
    """`mod.time` and `mod.urllib` are the shared modules, so `mod.time.sleep = ...`
    and `mod.urllib.request.urlopen = ...` below are process-wide patches. Restore
    BOTH: an unrestored sleep leaves
    `tests/test_wikidata_pacing.py::test_wd_pace_actually_waits` failing for anyone
    who runs this directory ahead of `tests/`. Same note as
    `test_wdqs_transport.py`.

    ⚠ `urlopen` was missing from here until 2026-09-16, while the docstring claimed
    parity with the sibling file that restores both. Nothing caught it because no
    later test in the suite used the real `urlopen` — so the leak was invisible
    exactly until one did, and then it failed in the *other* file with
    `AttributeError: 'str' object has no attribute 'full_url'` raised from a
    `fake_urlopen` defined in THIS one. A half-restored fixture is worse than none:
    it reads as the guard being present.
    """
    sleep, urlopen = time.sleep, urllib.request.urlopen
    try:
        yield
    finally:
        time.sleep, urllib.request.urlopen = sleep, urlopen


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_t_desc_fixes", os.path.join(MQ, "generate_description_fixes.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_short_read_is_retried_then_succeeds():
    """The behaviour, driven through the real function with the transport faked."""
    mod = _mod()
    calls = {"n": 0}

    class _Resp:
        status = 200
        def __init__(self, body): self._body = body
        def read(self, *a): return self._body
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(b'{"results": {"bindings": [{"x": {"value": "tru')
        return _Resp(b'{"results": {"bindings": [{"x": {"value": "ok"}}]}}')

    mod.urllib.request.urlopen = fake_urlopen
    mod.time.sleep = lambda *_: None          # do not actually wait 30s
    mod.WDQS_THROTTLE = 0
    out = mod.sparql("SELECT * WHERE {}")
    assert calls["n"] == 2, f"the short read was not retried ({calls['n']} call(s))"
    assert out == [{"x": {"value": "ok"}}]


def test_429_still_bails_without_retrying():
    """CLAUDE.md: 429 -> bail immediately, no retries. Widening the retry set must
    not have swept that up."""
    mod = _mod()
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

    mod.urllib.request.urlopen = fake_urlopen
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.sparql("SELECT * WHERE {}")
    except SystemExit as e:
        assert "429" in str(e)
    else:
        raise AssertionError("429 did not bail")
    assert calls["n"] == 1, f"429 was retried {calls['n']} times"


def test_the_retryable_set_names_the_short_read():
    src = inspect.getsource(_mod().sparql)
    assert "json.JSONDecodeError" in src, (
        "a truncated body is not in the retryable set again; one short read ends "
        "the whole sweep")
    for name in ("urllib.error.URLError", "TimeoutError"):
        assert name in src, f"{name} is no longer retried"


def test_the_backoff_is_the_repo_pattern_not_the_linear_one_this_file_invented():
    """15/45/135 over FOUR attempts, measured by driving the real function.

    This file carried **30/60/90 over three** until 2026-09-16, and it is where
    `wdqs_transport.py` was copied from — so the shared module shipped with the
    linear version for a day, and its docstring then described this file as having
    "the same policy" when the escalation did not match. CLAUDE.md names 15/45/135
    as the floor and `generate_genbu_ids.py` implements it.

    Four attempts, not three: at three only 15 and 45 ever fire and the documented
    third step never happens.
    """
    mod = _mod()
    waits = []
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = fake_urlopen
    mod.time.sleep = lambda s=0: waits.append(s)
    mod.WDQS_THROTTLE = 0
    with pytest.raises(mod.urllib.error.HTTPError):
        mod.sparql("SELECT * WHERE {}")
    assert calls["n"] == mod.RETRIES == 4, f"{calls['n']} attempts, RETRIES={mod.RETRIES}"
    # The throttle is patched to 0 but still calls sleep(0) once before the loop.
    assert [w for w in waits if w] == [15, 45, 135], waits


def test_a_client_error_is_not_retried():
    """A 414 cannot succeed on a retry, and this transport is the likelier of the
    two to see one: it sends the query in a GET URL and this script builds VALUES
    batches. wdqs_transport learned it on 2026-09-15 at a cost of three minutes of
    dutiful backoff."""
    mod = _mod()
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 414, "URI Too Long", {}, None)

    mod.urllib.request.urlopen = fake_urlopen
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    with pytest.raises(mod.urllib.error.HTTPError):
        mod.sparql("SELECT * WHERE {}")
    assert calls["n"] == 1, f"a 414 was retried {calls['n']} times"
