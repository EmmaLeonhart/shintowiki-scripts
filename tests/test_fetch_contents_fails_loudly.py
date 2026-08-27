"""A wiki outage must abort the plan, not shrink it.

Hit live on 2026-08-27 ~20:00Z: shinto.miraheze.org returned HTTP 502 on three
attempts with backoff, and the read died with a raw ``HTTPError`` traceback.

The traceback is the lesser problem. The real hazard is the tempting fix —
catching the error and returning whatever pages were read. An unmeasured page
counts as an ARTICLE in ``pick_canonical``, so dropping measurements silently
produces a DIFFERENT, smaller plan: fewer property-dump moves, more groups filed
as content merges. It would look complete, and someone could dispatch on it.

So ``fetch_contents`` retries with hard backoff and then raises ``WikiUnavailable``,
and the planner exits rather than planning from partial data.
"""
import os
import sys
import urllib.error

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "shinto_miraheze")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from shinto_miraheze import classify_duplicate_group_pages as mod  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch):
    """Backoff is real in production and pointless in a test."""
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)


def _always_502(*_a, **_k):
    raise urllib.error.HTTPError("u", 502, "Bad Gateway", {}, None)


def test_a_persistent_outage_raises_rather_than_returning_partial(monkeypatch):
    monkeypatch.setattr(mod.urllib.request, "urlopen", _always_502)
    with pytest.raises(mod.WikiUnavailable) as excinfo:
        mod.fetch_contents(["A", "B"])
    message = str(excinfo.value)
    assert "502" in message
    assert "No plan was built" in message


def test_it_retries_before_giving_up(monkeypatch):
    calls = {"n": 0}

    def counting(*_a, **_k):
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 502, "Bad Gateway", {}, None)

    monkeypatch.setattr(mod.urllib.request, "urlopen", counting)
    with pytest.raises(mod.WikiUnavailable):
        mod.fetch_contents(["A"])
    assert calls["n"] == len(mod.FETCH_RETRY_DELAYS) + 1


def test_a_transient_failure_recovers_without_raising(monkeypatch):
    """One 502 then success — the common case, and it must not abort."""
    state = {"n": 0}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"query": {"pages": [{"title": "A", "revisions": ' \
                   b'[{"slots": {"main": {"content": "hello"}}}]}]}}'

    def flaky(*_a, **_k):
        state["n"] += 1
        if state["n"] == 1:
            raise urllib.error.HTTPError("u", 502, "Bad Gateway", {}, None)
        return _Resp()

    monkeypatch.setattr(mod.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(mod.json, "load", lambda fh: __import__("json").loads(fh.read()))
    out = mod.fetch_contents(["A"])
    assert out == {"A": "hello"}
    assert state["n"] == 2


def test_wiki_unavailable_is_an_error_not_a_sentinel():
    """It must be raisable — a falsy return value would be silently ignored."""
    assert issubclass(mod.WikiUnavailable, Exception)
