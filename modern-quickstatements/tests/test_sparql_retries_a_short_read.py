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

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)


@pytest.fixture(autouse=True)
def _restore_sleep():
    """`mod.time` is the shared `time` module, so `mod.time.sleep = ...` below is a
    process-wide patch. Restore it: an unrestored one leaves
    `tests/test_wikidata_pacing.py::test_wd_pace_actually_waits` failing for anyone
    who runs this directory ahead of `tests/`. Same note as
    `test_wdqs_transport.py`."""
    sleep = time.sleep
    try:
        yield
    finally:
        time.sleep = sleep


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
