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

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

MIGRATED = ("generate_invalid_p825_removals.py",
            "generate_ronsha_role_qualifiers.py",
            "generate_misplaced_form_removals.py")


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


def test_the_copy_pasted_transports_are_gone():
    """These three carried the same function with no retry at all. If one grows its
    own urlopen back, it has left the shared policy behind."""
    for name in MIGRATED:
        src = open(os.path.join(MQ, name), encoding="utf-8").read()
        assert "import wdqs_transport" in src, f"{name} no longer uses the transport"
        assert "urllib.request.urlopen" not in src, (
            f"{name} calls urlopen directly again, outside the retry policy")
